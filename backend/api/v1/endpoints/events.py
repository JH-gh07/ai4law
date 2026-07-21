"""SSE 实时事件推送 + 轮询 fallback endpoint。"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.common.events.manager import get_ssemanager
from backend.common.runtime.run_manifest import load_run_manifest
from backend.common.trace.events import RunEvent
from backend.core.dependencies import get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.models.task import TaskOwnershipModel
from backend.services.task_access import require_task_access

logger = logging.getLogger(__name__)
router = APIRouter(tags=["events"])
OUTPUTS_DIR = Path("outputs")


@router.get("/task/{task_id}/stream")
async def task_event_stream(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """SSE 实时推送任务执行事件。"""
    require_task_access(db, task_id=task_id, user_id=current_user.id)

    async def event_generator():
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=256)
        sm = get_ssemanager()
        sm.subscribe(task_id, queue)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            sm.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/task/{task_id}/events")
async def task_events_since(
    task_id: str,
    since: int = Query(0, ge=-1),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """轮询 fallback：拉取 seq > since 的增量事件；-1 表示尚未消费事件。"""
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    sm = get_ssemanager()
    events = sm.get_events_since(task_id, since)
    latest_seq = events[-1].seq if events else since
    return {
        "events": [e.model_dump() for e in events],
        "latest_seq": latest_seq,
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
