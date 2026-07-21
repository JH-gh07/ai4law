import time

from backend.common.events.manager import get_ssemanager
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
