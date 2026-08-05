"""SSEManager — 管理 SSE 订阅连接和事件分发。"""

from __future__ import annotations

import asyncio
import secrets
import time
from threading import Lock
from typing import Any

from sqlalchemy.orm import sessionmaker

from backend.common.events.store import EventLog
from backend.common.trace.events import RunEvent

# stream_token 过期时间（秒）
STREAM_TOKEN_TTL_SECONDS = 300  # 5 分钟


class SSEManager:
    """内存事件队列管理器。task 完成后 30min 自动清理。"""

    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        self._task_events: dict[str, list[RunEvent]] = {}
        self._task_queues: dict[str, list[asyncio.Queue[RunEvent]]] = {}
        self._completed_at: dict[str, float] = {}
        self._latest_seq: dict[str, int] = {}
        self._publish_lock = Lock()
        # stream_token → (task_id, user_id, expires_at)
        self._stream_tokens: dict[str, tuple[str, str, float]] = {}
        self._token_lock = Lock()
        self._event_log = EventLog(session_factory) if session_factory is not None else None

    def configure_persistence(self, session_factory: sessionmaker) -> None:
        self._event_log = EventLog(session_factory)

    # ── Stream token management ──────────────────────────────────────

    def issue_stream_token(self, task_id: str, user_id: str) -> str:
        """签发任务绑定的短期 token，用于 EventSource 鉴权。

        返回一个随机 hex token。token 绑定到 (task_id, user_id)，
        5 分钟后自动过期。"""
        token = secrets.token_hex(32)
        expires_at = time.time() + STREAM_TOKEN_TTL_SECONDS
        if self._event_log is not None:
            self._event_log.store_stream_token(token, task_id, user_id, expires_at)
            return token
        with self._token_lock:
            self._stream_tokens[token] = (task_id, user_id, expires_at)
            self._expire_stream_tokens_locked()
        return token

    def verify_stream_token(self, token: str) -> tuple[str, str] | None:
        """验证 stream_token，返回 (task_id, user_id) 或 None。"""
        if self._event_log is not None:
            entry = self._event_log.get_stream_token(token)
            return (entry[0], entry[1]) if entry is not None else None
        with self._token_lock:
            self._expire_stream_tokens_locked()
            entry = self._stream_tokens.get(token)
            if entry is None:
                return None
            task_id, user_id, expires_at = entry
            if time.time() > expires_at:
                return None
            return (task_id, user_id)

    def stream_token_expires_at(self, token: str) -> float | None:
        if self._event_log is not None:
            entry = self._event_log.get_stream_token(token)
            return entry[2] if entry is not None else None
        with self._token_lock:
            self._expire_stream_tokens_locked()
            entry = self._stream_tokens.get(token)
            return entry[2] if entry is not None else None

    def _expire_stream_tokens_locked(self) -> None:
        """清理已过期的 token（需持有 _token_lock）。"""
        now = time.time()
        expired = [t for t, (_, _, exp) in self._stream_tokens.items() if now > exp]
        for t in expired:
            self._stream_tokens.pop(t, None)

    def subscribe(
        self,
        task_id: str,
        queue: asyncio.Queue[RunEvent],
        since: int = -1,
    ) -> None:
        """注册 SSE 连接并回放历史事件。"""
        if task_id not in self._task_queues:
            self._task_queues[task_id] = []
        self._task_queues[task_id].append(queue)
        for event in self.get_events_since(task_id, since):
            queue.put_nowait(event)

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        if task_id in self._task_queues:
            try:
                self._task_queues[task_id].remove(queue)
            except ValueError:
                pass

    def publish(self, task_id: str, event: RunEvent) -> None:
        """推送事件，并为不同事件源统一生成严格递增的传输序号。"""
        with self._publish_lock:
            if self._event_log is not None:
                event = self._event_log.append(task_id, event)
                previous_seq = self._latest_seq.get(task_id, -1)
                if event.seq <= previous_seq and any(
                    existing.event_id == event.event_id
                    for existing in self._task_events.get(task_id, [])
                ):
                    return
                transport_seq = event.seq
            else:
                previous_seq = self._latest_seq.get(task_id, -1)
                transport_seq = event.seq if event.seq > previous_seq else previous_seq + 1
                if transport_seq != event.seq:
                    event = event.model_copy(update={"seq": transport_seq})
            self._latest_seq[task_id] = transport_seq
            if task_id not in self._task_events:
                self._task_events[task_id] = []
            self._task_events[task_id].append(event)
        event_state = event.detail.get("state") if isinstance(event.detail, dict) else None
        if event.event_type in ("final", "final_brief") or event_state in {
            "COMPLETED",
            "FAILED",
            "CANCELED",
        }:
            self._completed_at[task_id] = time.time()
        for queue in self._task_queues.get(task_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def get_events_since(
        self,
        task_id: str,
        since: int,
        limit: int | None = None,
    ) -> list[RunEvent]:
        """轮询用：返回 seq > since 的事件。"""
        if self._event_log is not None:
            return self._event_log.list_since(task_id, since, limit=limit)
        events = [e for e in self._task_events.get(task_id, []) if e.seq > since]
        return events[:limit] if limit is not None else events

    def cleanup_expired(self, ttl_seconds: int = 1800) -> int:
        """清理已完成超过 ttl 的 task 事件数据。返回清理数量。"""
        now = time.time()
        expired = [tid for tid, ts in self._completed_at.items() if now - ts > ttl_seconds]
        for tid in expired:
            self._task_events.pop(tid, None)
            self._task_queues.pop(tid, None)
            self._completed_at.pop(tid, None)
            self._latest_seq.pop(tid, None)
        return len(expired)

    def clear_task(self, task_id: str) -> None:
        """显式删除某个 task 的内存事件与订阅痕迹。"""
        if self._event_log is not None:
            self._event_log.delete_task(task_id)
        self._task_events.pop(task_id, None)
        self._task_queues.pop(task_id, None)
        self._completed_at.pop(task_id, None)
        self._latest_seq.pop(task_id, None)

    def on_event(self, event: RunEvent) -> None:
        """作为 TraceRecorder 订阅者的回调入口。"""
        if event.task_id:
            self.publish(event.task_id, event)


# 全局单例
_ssemanager: SSEManager | None = None


def get_ssemanager(session_factory: sessionmaker | None = None) -> SSEManager:
    global _ssemanager
    if _ssemanager is None:
        _ssemanager = SSEManager(session_factory=session_factory)
    elif session_factory is not None:
        _ssemanager.configure_persistence(session_factory)
    return _ssemanager
