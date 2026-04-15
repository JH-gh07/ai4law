import time

from backend.common.tasks.manager import InMemoryTaskManager


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
