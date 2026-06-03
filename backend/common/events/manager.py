"""SSEManager — 管理 SSE 订阅连接和事件分发。"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from backend.common.trace.events import RunEvent


class SSEManager:
    """内存事件队列管理器。task 完成后 30min 自动清理。"""

    def __init__(self) -> None:
        self._task_events: dict[str, list[RunEvent]] = {}
        self._task_queues: dict[str, list[asyncio.Queue[RunEvent]]] = {}
        self._completed_at: dict[str, float] = {}

    def subscribe(self, task_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        """注册 SSE 连接并回放历史事件。"""
        if task_id not in self._task_queues:
            self._task_queues[task_id] = []
        self._task_queues[task_id].append(queue)
        for event in self._task_events.get(task_id, []):
            queue.put_nowait(event)

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        if task_id in self._task_queues:
            try:
                self._task_queues[task_id].remove(queue)
            except ValueError:
                pass

    def publish(self, task_id: str, event: RunEvent) -> None:
        """推送事件到所有对应 task 的活跃 SSE 连接。"""
        if task_id not in self._task_events:
            self._task_events[task_id] = []
        self._task_events[task_id].append(event)
        if event.event_type in ("final", "final_brief"):
            self._completed_at[task_id] = time.time()
        for queue in self._task_queues.get(task_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def get_events_since(self, task_id: str, since: int) -> list[RunEvent]:
        """轮询用：返回 seq > since 的事件。"""
        return [e for e in self._task_events.get(task_id, []) if e.seq > since]

    def cleanup_expired(self, ttl_seconds: int = 1800) -> int:
        """清理已完成超过 ttl 的 task 事件数据。返回清理数量。"""
        now = time.time()
        expired = [tid for tid, ts in self._completed_at.items() if now - ts > ttl_seconds]
        for tid in expired:
            self._task_events.pop(tid, None)
            self._task_queues.pop(tid, None)
            self._completed_at.pop(tid, None)
        return len(expired)

    def on_event(self, event: RunEvent) -> None:
        """作为 TraceRecorder 订阅者的回调入口。"""
        if event.task_id:
            self.publish(event.task_id, event)


# 全局单例
_ssemanager: SSEManager | None = None


def get_ssemanager() -> SSEManager:
    global _ssemanager
    if _ssemanager is None:
        _ssemanager = SSEManager()
    return _ssemanager
