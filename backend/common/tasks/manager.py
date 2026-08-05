from __future__ import annotations

import uuid
from copy import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock
import time
from typing import Any, Callable

from backend.common.tasks.cancellation import TaskCancelled, current_cancel_event


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
    provider_snapshot: dict[str, Any] | None
    manifest_path: str | None


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
    provider_snapshot: dict[str, Any] | None
    input_snapshot: Any
    trace_recorder: Any | None
    manifest_path: Path | None
    created_monotonic: float
    cancel_event: Event


class InMemoryTaskManager:
    """Lightweight async executor with task status and retry support."""

    def __init__(self, module: str, max_workers: int = 2) -> None:
        self.module = module
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"{module}-task")
        self._tasks: dict[str, _TaskRecord] = {}
        self._lock = Lock()

    def submit(
        self,
        runner: Callable[[], Any],
        max_attempts: int = 2,
        llm_client: Any | None = None,
    ) -> TaskSnapshot:
        now = _utc_now_iso()
        task_id = str(uuid.uuid4())
        wrapped_runner, provider_snapshot = self._bind_llm_snapshot(
            runner,
            llm_client,
        )
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
            provider_snapshot=provider_snapshot,
            input_snapshot={},
            trace_recorder=None,
            manifest_path=None,
            created_monotonic=time.monotonic(),
            cancel_event=Event(),
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
        llm_client: Any | None = None,
        input_snapshot: Any = None,
    ) -> TaskSnapshot:
        """提交任务并绑定 TraceRecorder 用于事件推送。"""
        now = _utc_now_iso()
        task_id = getattr(trace_recorder, "_task_id", "") or str(uuid.uuid4())

        # 将 task_id 注入 TraceRecorder，使 record() 发布的 RunEvent 带正确的 task_id
        trace_recorder._task_id = task_id
        if hasattr(trace_recorder, "trace_dir"):
            try:
                trace_recorder.trace_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        # 将 SSEManager 注册为 TraceRecorder 订阅者
        from backend.common.events.manager import get_ssemanager
        sm = get_ssemanager()
        trace_recorder.subscribe(sm.on_event)

        # 包裹 runner：注入 TraceRecorder 到 contextvar
        frozen_runner, provider_snapshot = self._bind_llm_snapshot(
            runner,
            llm_client,
        )

        def wrapped_runner():
            from backend.common.trace.context import current_trace
            token = current_trace.set(trace_recorder)
            try:
                return frozen_runner()
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
            provider_snapshot=provider_snapshot,
            input_snapshot=input_snapshot if input_snapshot is not None else {},
            trace_recorder=trace_recorder,
            manifest_path=trace_recorder.trace_dir.parent / "run_manifest.json",
            created_monotonic=time.monotonic(),
            cancel_event=Event(),
        )
        with self._lock:
            self._tasks[task_id] = record
        self._persist_manifest(record)

        # 必须先发布 CREATED 再启动线程，保证历史事件顺序稳定。
        from backend.common.trace.events import RunEvent
        sm.publish(task_id, RunEvent(
            task_id=task_id,
            seq=0,
            event_type="status",
            summary=f"任务已创建 ({self.module})",
            detail={"module": self.module, "state": "CREATED"},
        ))
        self._executor.submit(self._execute, task_id)

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
            record.cancel_event.clear()
        self._persist_manifest(record)
        self._executor.submit(self._execute, task_id)
        return self.get_or_raise(task_id)

    def cancel(self, task_id: str) -> TaskSnapshot:
        trace_recorder = None
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                raise KeyError(f"Task not found: {task_id}")
            if record.state in {"COMPLETED", "FAILED", "CANCELED"}:
                return self._snapshot(record)
            record.state = "CANCELED"
            record.updated_at = _utc_now_iso()
            record.cancel_event.set()
            trace_recorder = record.trace_recorder
        self._persist_manifest(record)
        payload = {
            "summary": f"任务已取消 ({self.module})",
            "detail": {"module": self.module, "state": "CANCELED"},
        }
        if trace_recorder is not None:
            try:
                trace_recorder.record("task_canceled", payload)
                trace_recorder.write_manifest()
            except Exception:
                pass
            finally:
                self._persist_manifest(record)
        else:
            from backend.common.events.manager import get_ssemanager
            from backend.common.trace.events import RunEvent

            get_ssemanager().publish(
                task_id,
                RunEvent(
                    task_id=task_id,
                    seq=0,
                    event_type="status",
                    summary=payload["summary"],
                    detail=payload["detail"],
                ),
            )
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

            # 各事件源可从 0/1 自行计数，SSEManager 统一生成传输序号。
            from backend.common.events.manager import get_ssemanager
            from backend.common.trace.events import RunEvent
            sm = get_ssemanager()
            sm.publish(task_id, RunEvent(
                task_id=task_id,
                seq=0,
                event_type="status",
                summary=f"任务开始执行 ({self.module})",
                detail={"module": self.module, "state": "RUNNING"},
            ))
        self._persist_manifest(record)

        try:
            cancel_token = current_cancel_event.set(record.cancel_event)
            try:
                result = record.runner()
            finally:
                current_cancel_event.reset(cancel_token)
            if record.cancel_event.is_set():
                return
            trace_recorder = record.trace_recorder
            if hasattr(result, "model_dump"):
                payload = result.model_dump()  # pydantic model
            elif isinstance(result, dict):
                payload = result
            else:
                payload = {"value": result}

            try:
                if hasattr(trace_recorder, "_events"):
                    event_names = {getattr(item, "name", "") for item in getattr(trace_recorder, "_events", [])}
                else:
                    event_names = set()
                if "final" not in event_names or "final_brief" not in event_names:
                    from backend.common.trace.finalization import build_success_events

                    final_payload, brief_payload = build_success_events(self.module, payload)
                    if "final" not in event_names:
                        trace_recorder.record("final", final_payload)
                    if "final_brief" not in event_names:
                        trace_recorder.record("final_brief", brief_payload)
            except Exception:
                pass

            try:
                output_files = payload.get("output_files") if isinstance(payload, dict) else None
                sample_path = None
                if isinstance(output_files, dict):
                    for value in output_files.values():
                        if isinstance(value, str) and value.strip():
                            sample_path = value
                            break
                if sample_path:
                    from pathlib import Path
                    from backend.common.citation.output import synthesize_citation_map, write_citation_map_json

                    output_dir = Path(sample_path).parent
                    citation_map_path = output_dir / "citation_map.json"
                    if not citation_map_path.exists():
                        footnote_map, all_items = synthesize_citation_map(
                            module=self.module,
                            task_id=task_id,
                            payload=payload,
                        )
                        write_citation_map_json(
                            output_dir=output_dir,
                            module=self.module,
                            task_id=task_id,
                            footnote_map=footnote_map,
                            all_items=all_items,
                        )
            except Exception:
                pass

            try:
                from backend.common.trace.finalization import build_success_events
            except Exception:
                pass

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
                    seq=0,
                    event_type="status",
                    summary=f"任务执行完成 ({self.module})",
                    detail={"module": self.module, "state": "COMPLETED"},
                ))
            if trace_recorder is not None:
                trace_recorder.write_manifest()
            self._persist_manifest(current)
        except TaskCancelled:
            return
        except Exception as exc:
            trace_recorder = record.trace_recorder
            try:
                from backend.common.trace.finalization import build_failure_events

                final_payload, brief_payload = build_failure_events(self.module, f"{exc.__class__.__name__}: {exc}")
                trace_recorder.record("final", final_payload)
                trace_recorder.record("final_brief", brief_payload)
            except Exception:
                pass
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
                    seq=0,
                    event_type="status",
                    summary=f"任务执行失败: {exc}",
                    detail={"module": self.module, "state": "FAILED", "error": str(exc)},
                ))
            if trace_recorder is not None:
                trace_recorder.write_manifest()
            self._persist_manifest(current)

    @staticmethod
    def _persist_manifest(record: _TaskRecord) -> None:
        if record.manifest_path is None or record.trace_recorder is None:
            return
        from backend.common.runtime.run_manifest import write_run_manifest

        write_run_manifest(
            record.manifest_path,
            run_id=record.task_id,
            module=record.module,
            status=record.state,
            created_at=record.created_at,
            updated_at=record.updated_at,
            attempts=record.attempts,
            max_attempts=record.max_attempts,
            duration_ms=int((time.monotonic() - record.created_monotonic) * 1000),
            provider_snapshot=record.provider_snapshot,
            input_snapshot=record.input_snapshot,
            result=record.result,
            error=record.error,
            trace_recorder=record.trace_recorder,
        )

    @staticmethod
    def _bind_llm_snapshot(
        runner: Callable[[], Any],
        llm_client: Any | None,
    ) -> tuple[Callable[[], Any], dict[str, Any] | None]:
        if llm_client is None:
            return runner, None

        clone = getattr(llm_client, "clone", None)
        frozen_client = clone() if callable(clone) else copy(llm_client)
        snapshot_factory = getattr(frozen_client, "provider_snapshot", None)
        if callable(snapshot_factory):
            provider_snapshot = snapshot_factory().sanitized()
        else:
            provider_snapshot = {
                "provider_id": type(frozen_client).__name__,
                "snapshot_supported": False,
            }

        def scoped_runner() -> Any:
            from backend.common.llm.context import current_llm_client

            token = current_llm_client.set(frozen_client)
            try:
                return runner()
            finally:
                current_llm_client.reset(token)

        return scoped_runner, provider_snapshot

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
            provider_snapshot=record.provider_snapshot,
            manifest_path=str(record.manifest_path) if record.manifest_path else None,
        )
