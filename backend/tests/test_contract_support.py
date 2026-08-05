from pathlib import Path

from backend.app import create_app
from backend.core.settings import Settings
from backend.domains.eu.dpia import router as dpia_router
from backend.tests.contract_support import (
    ContractExternalNetworkError,
    LocalhostOnlyNetworkGuard,
    RecordingExecutor,
    RecordingTaskDispatcher,
    install_recording_execution,
)


def test_recording_executor_records_without_running_callable() -> None:
    executor = RecordingExecutor()
    calls: list[str] = []

    future = executor.submit(lambda: calls.append("executed"))

    assert calls == []
    assert executor.submission_count == 1
    assert future.done()
    assert future.result() is None


def test_recording_dispatcher_records_without_running_callable() -> None:
    dispatcher = RecordingTaskDispatcher()
    calls: list[str] = []

    future = dispatcher.dispatch(lambda: calls.append("executed"))

    assert calls == []
    assert dispatcher.submission_count == 1
    assert future.done()
    assert future.result() is None


def test_install_recording_execution_covers_all_async_services_and_restores(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            app_env="test",
            database_url=f"sqlite:///{tmp_path / 'contract.db'}",
            storage_dir=tmp_path / "storage",
            llm_provider="none",
            delilegal_app_id=None,
            delilegal_secret=None,
            rag_auto_build_index=False,
            _env_file=None,
        )
    )
    original_dpia_executor = dpia_router.service.tasks._executor
    original_review_dispatcher = app.state.container.review_service.task_dispatcher
    isolation = install_recording_execution(app)
    calls: list[str] = []

    try:
        accepted = dpia_router.service.tasks.submit(lambda: calls.append("executed"))
        review_future = app.state.container.review_service.task_dispatcher.dispatch(
            lambda: calls.append("review-executed")
        )

        assert accepted.state == "CREATED"
        assert calls == []
        assert review_future.done()
        assert len(isolation.manager_executors) == 9
        assert isolation.submission_count == 2
    finally:
        isolation.restore()

    assert dpia_router.service.tasks._executor is original_dpia_executor
    assert app.state.container.review_service.task_dispatcher is original_review_dispatcher


def test_localhost_network_guard_blocks_external_connect_and_restores() -> None:
    guard = LocalhostOnlyNetworkGuard()
    guard.install()

    try:
        guard.check_address(("203.0.113.10", 443))
    except ContractExternalNetworkError as exc:
        assert "203.0.113.10" in str(exc)
    else:
        raise AssertionError("external address was not blocked")
    finally:
        guard.restore()

    guard.check_address(("127.0.0.1", 8000))
