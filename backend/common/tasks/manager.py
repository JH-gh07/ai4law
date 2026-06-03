from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskSnapshot:
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None
    result: dict[str, Any] | None


@dataclass
class _TaskRecord:
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None
    result: dict[str, Any] | None
    runner: Callable[[], Any]


class InMemoryTaskManager:
    """Lightweight async executor with task status and retry support."""

    def __init__(self, module: str, max_workers: int = 2) -> None:
        self.module = module
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"{module}-task")
        self._tasks: dict[str, _TaskRecord] = {}
        self._lock = Lock()

    def submit(self, runner: Callable[[], Any], max_attempts: int = 2) -> TaskSnapshot:
        now = _utc_now_iso()
        task_id = str(uuid.uuid4())
        record = _TaskRecord(
            task_id=task_id,
            module=self.module,
            state="CREATED",
            attempts=0,
            max_attempts=max(1, max_attempts),
            created_at=now,
            updated_at=now,
            error=None,
            result=None,
            runner=runner,
        )
        with self._lock:
            self._tasks[task_id] = record
        self._executor.submit(self._execute, task_id)
        return self.get_or_raise(task_id)

    def submit_with_trace(
        self,
        runner: Callable[[], Any],
        trace_recorder: Any,  # TraceRecorder
        max_attempts: int = 2,
    ) -> TaskSnapshot:
        """提交任务并绑定 TraceRecorder 用于事件推送。"""
        now = _utc_now_iso()
        task_id = str(uuid.uuid4())

        # 将 SSEManager 注册为 TraceRecorder 订阅者
        from backend.common.events.manager import get_ssemanager
        sm = get_ssemanager()
        trace_recorder.subscribe(sm.on_event)

        # 包裹 runner：注入 TraceRecorder 到 contextvar
        def wrapped_runner():
            from backend.common.trace.context import current_trace
            token = current_trace.set(trace_recorder)
            try:
                return runner()
            finally:
                current_trace.reset(token)

        record = _TaskRecord(
            task_id=task_id,
            module=self.module,
            state="CREATED",
            attempts=0,
            max_attempts=max(1, max_attempts),
            created_at=now,
            updated_at=now,
            error=None,
            result=None,
            runner=wrapped_runner,
        )
        with self._lock:
            self._tasks[task_id] = record
        self._executor.submit(self._execute, task_id)

        # 发布 status 事件
        from backend.common.trace.events import RunEvent
        sm.publish(task_id, RunEvent(
            task_id=task_id,
            seq=0,
            event_type="status",
            summary=f"任务已创建 ({self.module})",
            detail={"module": self.module, "state": "CREATED"},
        ))

        return self.get_or_raise(task_id)

    def get(self, task_id: str) -> TaskSnapshot | None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return None
            return self._snapshot(record)

    def get_or_raise(self, task_id: str) -> TaskSnapshot:
        snapshot = self.get(task_id)
        if snapshot is None:
            raise KeyError(f"Task not found: {task_id}")
        return snapshot

    def retry(self, task_id: str) -> TaskSnapshot:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                raise KeyError(f"Task not found: {task_id}")
            if record.state in {"RUNNING", "RETRYING", "CREATED"}:
                return self._snapshot(record)
            if record.state == "COMPLETED":
                return self._snapshot(record)
            if record.attempts >= record.max_attempts:
                return self._snapshot(record)
            record.state = "RETRYING"
            record.updated_at = _utc_now_iso()
            record.error = None
            record.result = None
        self._executor.submit(self._execute, task_id)
        return self.get_or_raise(task_id)

    def cancel(self, task_id: str) -> TaskSnapshot:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                raise KeyError(f"Task not found: {task_id}")
            if record.state in {"COMPLETED", "FAILED", "CANCELED"}:
                return self._snapshot(record)
            record.state = "CANCELED"
            record.updated_at = _utc_now_iso()
        return self.get_or_raise(task_id)

    def _execute(self, task_id: str) -> None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return
            if record.state == "CANCELED":
                return
            record.state = "RUNNING"
            record.attempts += 1
            record.updated_at = _utc_now_iso()

            # 新增：发布 RUNNING 状态事件
            from backend.common.events.manager import get_ssemanager
            from backend.common.trace.events import RunEvent
            sm = get_ssemanager()
            sm.publish(task_id, RunEvent(
                task_id=task_id,
                seq=-1,
                event_type="status",
                summary=f"任务开始执行 ({self.module})",
                detail={"module": self.module, "state": "RUNNING"},
            ))

        try:
            result = record.runner()
            if hasattr(result, "model_dump"):
                payload = result.model_dump()  # pydantic model
            elif isinstance(result, dict):
                payload = result
            else:
                payload = {"value": result}

            with self._lock:
                current = self._tasks.get(task_id)
                if current is None:
                    return
                if current.state == "CANCELED":
                    return
                current.state = "COMPLETED"
                current.updated_at = _utc_now_iso()
                current.error = None
                current.result = payload

                # 新增：发布 COMPLETED 状态
                sm.publish(task_id, RunEvent(
                    task_id=task_id,
                    seq=-1,
                    event_type="status",
                    summary=f"任务执行完成 ({self.module})",
                    detail={"module": self.module, "state": "COMPLETED"},
                ))
        except Exception as exc:
            with self._lock:
                current = self._tasks.get(task_id)
                if current is None:
                    return
                if current.state == "CANCELED":
                    return
                current.state = "FAILED"
                current.updated_at = _utc_now_iso()
                current.error = f"{exc.__class__.__name__}: {exc}"
                current.result = None

                # 新增：发布 FAILED 状态
                sm.publish(task_id, RunEvent(
                    task_id=task_id,
                    seq=-1,
                    event_type="status",
                    summary=f"任务执行失败: {exc}",
                    detail={"module": self.module, "state": "FAILED", "error": str(exc)},
                ))

    @staticmethod
    def _snapshot(record: _TaskRecord) -> TaskSnapshot:
        return TaskSnapshot(
            task_id=record.task_id,
            module=record.module,
            state=record.state,
            attempts=record.attempts,
            max_attempts=record.max_attempts,
            created_at=record.created_at,
            updated_at=record.updated_at,
            error=record.error,
            result=record.result,
        )
