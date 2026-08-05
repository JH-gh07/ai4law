from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from threading import Lock
from typing import Any

from fastapi import FastAPI

from backend.domains.cn.pipia import router as pipia_router
from backend.domains.cn.security_assessment import router as assessment_router
from backend.domains.eu.bcr_review import router as bcr_router
from backend.domains.eu.dpia import router as dpia_router
from backend.domains.eu.scc_review import router as eu_scc_router
from backend.domains.eu.tia import router as tia_router
from backend.domains.us.cpra import router as cpra_router
from backend.domains.us.eo14117 import router as us_14117_router
from backend.domains.us.eo14117_flow_review import router as cn_flow_router


class RecordingExecutor:
    """Accept executor submissions without running or retaining their callables."""

    def __init__(self) -> None:
        self._submission_count = 0
        self._lock = Lock()

    @property
    def submission_count(self) -> int:
        with self._lock:
            return self._submission_count

    def submit(self, _func, *_args, **_kwargs) -> Future[None]:
        with self._lock:
            self._submission_count += 1
        future: Future[None] = Future()
        future.set_result(None)
        return future


class RecordingTaskDispatcher:
    """Review task dispatcher that records dispatch without executing pipelines."""

    def __init__(self) -> None:
        self._executor = RecordingExecutor()

    @property
    def submission_count(self) -> int:
        return self._executor.submission_count

    def dispatch(self, func, *args, **kwargs) -> Future[None]:
        return self._executor.submit(func, *args, **kwargs)


_MANAGER_TARGETS = {
    "assessment": assessment_router.service.tasks,
    "pipia": pipia_router.service.tasks,
    "eu_scc": eu_scc_router.service.tasks,
    "bcr": bcr_router.service.tasks,
    "dpia": dpia_router.service.tasks,
    "tia": tia_router.service.tasks,
    "cn_flow": cn_flow_router.service.tasks,
    "us_14117": us_14117_router.service.tasks,
    "cpra": cpra_router.service.tasks,
}


@dataclass
class _ManagerExecutorBinding:
    manager: Any
    original_executor: Any
    recording_executor: RecordingExecutor


class RecordingExecutionIsolation:
    def __init__(
        self,
        *,
        manager_bindings: dict[str, _ManagerExecutorBinding],
        review_service: Any,
        original_review_dispatcher: Any,
        review_dispatcher: RecordingTaskDispatcher,
    ) -> None:
        self._manager_bindings = manager_bindings
        self._review_service = review_service
        self._original_review_dispatcher = original_review_dispatcher
        self.review_dispatcher = review_dispatcher
        self._restored = False

    @property
    def manager_executors(self) -> dict[str, RecordingExecutor]:
        return {
            module: binding.recording_executor
            for module, binding in self._manager_bindings.items()
        }

    @property
    def submission_count(self) -> int:
        return sum(
            binding.recording_executor.submission_count
            for binding in self._manager_bindings.values()
        ) + self.review_dispatcher.submission_count

    def restore(self) -> None:
        if self._restored:
            return
        for binding in self._manager_bindings.values():
            if binding.manager._executor is binding.recording_executor:
                binding.manager._executor = binding.original_executor
        if self._review_service.task_dispatcher is self.review_dispatcher:
            self._review_service.task_dispatcher = self._original_review_dispatcher
        self._restored = True


def install_recording_execution(app: FastAPI) -> RecordingExecutionIsolation:
    manager_bindings: dict[str, _ManagerExecutorBinding] = {}
    for module, manager in _MANAGER_TARGETS.items():
        original_executor = manager._executor
        recording_executor = RecordingExecutor()
        manager._executor = recording_executor
        manager_bindings[module] = _ManagerExecutorBinding(
            manager=manager,
            original_executor=original_executor,
            recording_executor=recording_executor,
        )

    review_service = app.state.container.review_service
    original_review_dispatcher = review_service.task_dispatcher
    review_dispatcher = RecordingTaskDispatcher()
    review_service.task_dispatcher = review_dispatcher

    return RecordingExecutionIsolation(
        manager_bindings=manager_bindings,
        review_service=review_service,
        original_review_dispatcher=original_review_dispatcher,
        review_dispatcher=review_dispatcher,
    )
