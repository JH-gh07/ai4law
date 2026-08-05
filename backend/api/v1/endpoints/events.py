"""SSE 实时事件推送 + 轮询 fallback endpoint。"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.common.events.manager import get_ssemanager
from backend.common.runtime.run_manifest import load_run_manifest
from backend.common.trace.events import RunEvent
from backend.core.dependencies import get_current_user, get_current_user_optional, get_db
from backend.schemas.auth import AuthUser
from backend.models.task import TaskOwnershipModel
from backend.services.task_access import require_task_access

logger = logging.getLogger(__name__)
router = APIRouter(tags=["events"])
OUTPUTS_DIR = Path("outputs")


async def _stream_events(task_id: str, request: Request, since: int):
    """SSE event generator — 内部共用，鉴权在上层完成。"""
    queue: asyncio.Queue[RunEvent] = asyncio.Queue()
    sm = get_ssemanager()
    sm.subscribe(task_id, queue, since=since)
    latest_seq = since
    last_heartbeat = time.monotonic()
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1)
                if event.seq > latest_seq:
                    latest_seq = event.seq
                    yield f"id: {event.seq}\ndata: {event.model_dump_json()}\n\n"
            except asyncio.TimeoutError:
                for event in sm.get_events_since(task_id, latest_seq, limit=200):
                    latest_seq = event.seq
                    yield f"id: {event.seq}\ndata: {event.model_dump_json()}\n\n"
            if time.monotonic() - last_heartbeat >= 15:
                yield ": heartbeat\n\n"
                last_heartbeat = time.monotonic()
    finally:
        sm.unsubscribe(task_id, queue)


@router.get("/task/{task_id}/stream")
async def task_event_stream(
    task_id: str,
    request: Request,
    token: str | None = Query(default=None),
    since: int | None = Query(default=None, ge=-1),
    db: Session = Depends(get_db),
    current_user: AuthUser | None = Depends(get_current_user_optional),
):
    """SSE 实时推送任务执行事件。

    支持两种鉴权方式：
    1. ?token=<stream_token> query parameter（EventSource 兼容）
    2. Authorization: Bearer <token> header（fetch-based SSE / 开发调试）
    """
    if since is None:
        try:
            since = int(request.headers.get("last-event-id", "-1"))
        except ValueError:
            since = -1

    # 优先检查 query token
    if token is not None:
        sm = get_ssemanager()
        result = sm.verify_stream_token(token)
        if result is None:
            raise HTTPException(status_code=401, detail="Invalid or expired stream token")
        verified_task_id, _user_id = result
        if verified_task_id != task_id:
            raise HTTPException(status_code=403, detail="Stream token does not match task")
        return StreamingResponse(
            _stream_events(task_id, request, since),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Bearer token 鉴权
    if current_user is None:
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    return StreamingResponse(
        _stream_events(task_id, request, since),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/task/{task_id}/token")
def issue_stream_token(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """签发任务绑定的短期 stream token，供 EventSource 连接使用。

    前端在打开 SSE 连接前调用此端点获取短期 token，
    然后将 token 拼入 SSE URL 的 query string。
    token 有效期 5 分钟，绑定到当前 (task_id, user_id)。
    """
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    sm = get_ssemanager()
    stream_token = sm.issue_stream_token(task_id, current_user.id)
    expires_at = sm.stream_token_expires_at(stream_token)
    return {
        "stream_token": stream_token,
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
    }


@router.get("/task/{task_id}/events")
async def task_events_since(
    task_id: str,
    since: int = Query(0, ge=-1),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """轮询 fallback：拉取 seq > since 的增量事件；-1 表示尚未消费事件。"""
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    sm = get_ssemanager()
    page = sm.get_events_since(task_id, since, limit=limit + 1)
    has_more = len(page) > limit
    events = page[:limit]
    latest_seq = events[-1].seq if events else since
    return {
        "events": [e.model_dump() for e in events],
        "latest_seq": latest_seq,
        "has_more": has_more,
    }


@router.get("/task/{task_id}/manifest")
def task_run_manifest(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    ownership = db.get(TaskOwnershipModel, task_id)
    if ownership is None or ownership.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Run manifest not found")
    manifest = load_run_manifest(
        OUTPUTS_DIR,
        module=ownership.module,
        run_id=task_id,
    )
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run manifest not found")
    return manifest
