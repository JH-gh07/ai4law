from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor


class TaskDispatcher:
    def dispatch(self, func: Callable, *args, **kwargs):
        raise NotImplementedError


class InlineTaskDispatcher(TaskDispatcher):
    def dispatch(self, func: Callable, *args, **kwargs):
        return func(*args, **kwargs)


class ThreadedTaskDispatcher(TaskDispatcher):
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=4)

    def dispatch(self, func: Callable, *args, **kwargs):
        return self.executor.submit(func, *args, **kwargs)


def build_task_dispatcher(mode: str) -> TaskDispatcher:
    if mode == "threaded":
        return ThreadedTaskDispatcher()
    return InlineTaskDispatcher()
