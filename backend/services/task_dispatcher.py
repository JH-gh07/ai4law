"""
本文件用于定义任务调度器的接口和实现，包括同步和异步任务调度。
`TaskDispatcher` 是一个抽象基类，定义了 `dispatch` 方法。
`InlineTaskDispatcher` 实现了同步任务调度，
`ThreadedTaskDispatcher` 使用线程池实现了异步任务调度。
`build_task_dispatcher` 函数根据传入的模式创建相应的任务调度器实例。
"""
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
