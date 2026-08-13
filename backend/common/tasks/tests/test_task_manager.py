import time
import json
from dataclasses import dataclass
from pathlib import Path
from threading import Event

import pytest

from backend.common.events.manager import get_ssemanager
from backend.common.llm.context import current_llm_client
from backend.common.tasks.manager import InMemoryTaskManager, configure_task_persistence
from backend.common.tasks.cancellation import is_task_cancelled, raise_if_task_cancelled
from backend.common.trace.recorder import TraceRecorder
from backend.core.db import build_engine, build_session_factory, init_db


def wait_until_terminal(manager: InMemoryTaskManager, task_id: str, timeout: float = 3.0):
    start = time.time()
    while time.time() - start < timeout:
        snapshot = manager.get_or_raise(task_id)
        if snapshot.state in {"COMPLETED", "FAILED"}:
            return snapshot
        time.sleep(0.05)
    raise TimeoutError("task did not reach terminal state")


@pytest.fixture
def persisted_task_db(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'tasks.db'}")
    init_db(engine)
    session_factory = build_session_factory(engine)
    configure_task_persistence(session_factory)
    try:
        yield session_factory
    finally:
        configure_task_persistence(None)
        engine.dispose()


def test_task_manager_complete() -> None:
    manager = InMemoryTaskManager(module="ut")
    accepted = manager.submit(lambda: {"ok": True})

    snapshot = wait_until_terminal(manager, accepted.task_id)
    assert snapshot.state == "COMPLETED"
    assert snapshot.result == {"ok": True}


def test_second_manager_reads_completed_task_from_persistence(persisted_task_db) -> None:
    first_worker = InMemoryTaskManager(module="ut")
    accepted = first_worker.submit(lambda: {"ok": True, "value": 7})
    completed = wait_until_terminal(first_worker, accepted.task_id)
    assert completed.state == "COMPLETED"

    second_worker = InMemoryTaskManager(module="ut")
    recovered = second_worker.get_or_raise(accepted.task_id)

    assert recovered.state == "COMPLETED"
    assert recovered.attempts == 1
    assert recovered.max_attempts == 2
    assert recovered.result == {"ok": True, "value": 7}


def test_persisted_lookup_does_not_cross_module_boundary(persisted_task_db) -> None:
    first_worker = InMemoryTaskManager(module="ut")
    accepted = first_worker.submit(lambda: {"ok": True})
    wait_until_terminal(first_worker, accepted.task_id)

    other_module = InMemoryTaskManager(module="other")
    with pytest.raises(KeyError, match="Task not found"):
        other_module.get_or_raise(accepted.task_id)


def test_task_manager_retry() -> None:
    manager = InMemoryTaskManager(module="ut")
    counter = {"n": 0}

    def runner() -> dict[str, bool]:
        counter["n"] += 1
        if counter["n"] == 1:
            raise RuntimeError("first failure")
        return {"ok": True}

    accepted = manager.submit(runner, max_attempts=2)
    first = wait_until_terminal(manager, accepted.task_id)
    assert first.state == "FAILED"

    manager.retry(accepted.task_id)
    second = wait_until_terminal(manager, accepted.task_id)
    assert second.state == "COMPLETED"
    assert second.attempts == 2


def test_traced_task_events_have_one_monotonic_transport_sequence(tmp_path) -> None:
    import backend.common.events.manager as events_module

    events_module._ssemanager = None
    manager = InMemoryTaskManager(module="ut")
    recorder = TraceRecorder(tmp_path / "trace")

    def runner() -> dict[str, bool]:
        recorder.record("thought", {"summary": "业务追踪"})
        return {"ok": True}

    accepted = manager.submit_with_trace(runner, recorder)
    wait_until_terminal(manager, accepted.task_id)

    events = get_ssemanager().get_events_since(accepted.task_id, since=-1)
    sequences = [event.seq for event in events]
    assert sequences == sorted(set(sequences))
    assert [event.summary for event in events[:3]] == [
        "任务已创建 (ut)",
        "任务开始执行 (ut)",
        "业务追踪",
    ]


def test_cancel_publishes_terminal_event_without_late_success(tmp_path) -> None:
    import backend.common.events.manager as events_module

    events_module._ssemanager = None
    manager = InMemoryTaskManager(module="ut")
    recorder = TraceRecorder(tmp_path / "trace")
    started = Event()
    release = Event()
    returned = Event()

    def runner() -> dict[str, bool]:
        started.set()
        release.wait(timeout=2)
        returned.set()
        return {"ok": True}

    accepted = manager.submit_with_trace(runner, recorder)
    assert started.wait(timeout=2)

    canceled = manager.cancel(accepted.task_id)
    release.set()
    assert returned.wait(timeout=2)
    time.sleep(0.1)

    events = get_ssemanager().get_events_since(accepted.task_id, since=-1)
    canceled_events = [
        event
        for event in events
        if event.event_type == "status"
        and isinstance(event.detail, dict)
        and event.detail.get("state") == "CANCELED"
    ]
    assert canceled.state == "CANCELED"
    assert len(canceled_events) == 1
    assert all(event.event_type not in {"final", "final_brief"} for event in events)


def test_cooperative_cancellation_does_not_emit_failure_final(tmp_path) -> None:
    import backend.common.events.manager as events_module

    events_module._ssemanager = None
    manager = InMemoryTaskManager(module="ut")
    recorder = TraceRecorder(tmp_path / "trace")
    started = Event()
    stopped = Event()

    def runner() -> dict[str, bool]:
        started.set()
        while not is_task_cancelled():
            time.sleep(0.01)
        stopped.set()
        raise_if_task_cancelled()
        return {"ok": True}

    accepted = manager.submit_with_trace(runner, recorder)
    assert started.wait(timeout=2)
    manager.cancel(accepted.task_id)
    assert stopped.wait(timeout=2)
    time.sleep(0.1)

    events = get_ssemanager().get_events_since(accepted.task_id, since=-1)
    assert all(event.event_type not in {"final", "final_brief"} for event in events)


@dataclass(frozen=True)
class _FakeProviderSnapshot:
    label: str

    def sanitized(self) -> dict[str, str]:
        return {"provider_id": self.label, "fingerprint": f"fp-{self.label}"}


class _FakeLLMClient:
    def __init__(self, label: str) -> None:
        self.label = label

    def clone(self) -> "_FakeLLMClient":
        return _FakeLLMClient(self.label)

    def provider_snapshot(self) -> _FakeProviderSnapshot:
        return _FakeProviderSnapshot(self.label)


def test_task_keeps_submission_provider_snapshot_across_runtime_change() -> None:
    manager = InMemoryTaskManager(module="ut")
    release = Event()
    live_client = _FakeLLMClient("provider-a")

    def runner() -> dict[str, str]:
        release.wait(timeout=2)
        frozen_client = current_llm_client.get()
        return {"provider": frozen_client.label}

    accepted = manager.submit(runner, llm_client=live_client)
    live_client.label = "provider-b"
    release.set()

    snapshot = wait_until_terminal(manager, accepted.task_id)
    assert snapshot.result == {"provider": "provider-a"}
    assert snapshot.provider_snapshot == {
        "provider_id": "provider-a",
        "fingerprint": "fp-provider-a",
    }


def test_traced_task_persists_a_sanitized_run_manifest(tmp_path) -> None:
    manager = InMemoryTaskManager(module="ut")
    recorder = TraceRecorder(tmp_path / "run" / "trace", task_id="manifest-task")
    client = _FakeLLMClient("provider-a")

    def runner() -> dict[str, object]:
        recorder.record(
            "tool_result",
            {
                "summary": "模型返回",
                "detail": {
                    "tool": "llm_chat",
                    "usage": {
                        "prompt_tokens": 11,
                        "completion_tokens": 7,
                        "total_tokens": 18,
                    },
                },
            },
        )
        return {
            "report_path": "/tmp/report.md",
            "output_files": {"docx": "/tmp/report.docx"},
        }

    accepted = manager.submit_with_trace(
        runner,
        recorder,
        llm_client=client,
        input_snapshot={
            "company_name": "Highly Sensitive Co",
            "uploaded_files": [
                {"file_name": "contract.docx", "storage_uri": "storage://contract"}
            ],
        },
    )
    wait_until_terminal(manager, accepted.task_id)

    manifest_path = tmp_path / "run" / "run_manifest.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["schema_version"] == "1.0"
    assert manifest["run_id"] == "manifest-task"
    assert manifest["status"] == "COMPLETED"
    assert manifest["provider_snapshot"]["provider_id"] == "provider-a"
    assert manifest["input"]["fields"] == ["company_name", "uploaded_files"]
    assert manifest["input"]["artifacts"] == [
        {"file_name": "contract.docx", "storage_uri": "storage://contract"}
    ]
    assert manifest["output"]["artifacts"] == [
        {"role": "docx", "path": "/tmp/report.docx"},
        {"role": "report", "path": "/tmp/report.md"},
    ]
    assert manifest["observability"]["event_count"] >= 1
    assert manifest["observability"]["llm_calls"] == 1
    assert manifest["observability"]["tokens"]["total_tokens"] == 18
    assert manifest["duration_ms"] >= 0
    assert "Highly Sensitive Co" not in manifest_text
