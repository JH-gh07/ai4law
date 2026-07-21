import time
from dataclasses import dataclass
from threading import Event

from backend.common.events.manager import get_ssemanager
from backend.common.llm.context import current_llm_client
from backend.common.tasks.manager import InMemoryTaskManager
from backend.common.trace.recorder import TraceRecorder


def wait_until_terminal(manager: InMemoryTaskManager, task_id: str, timeout: float = 3.0):
    start = time.time()
    while time.time() - start < timeout:
        snapshot = manager.get_or_raise(task_id)
        if snapshot.state in {"COMPLETED", "FAILED"}:
            return snapshot
        time.sleep(0.05)
    raise TimeoutError("task did not reach terminal state")


def test_task_manager_complete() -> None:
    manager = InMemoryTaskManager(module="ut")
    accepted = manager.submit(lambda: {"ok": True})

    snapshot = wait_until_terminal(manager, accepted.task_id)
    assert snapshot.state == "COMPLETED"
    assert snapshot.result == {"ok": True}


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
