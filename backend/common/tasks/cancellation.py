from __future__ import annotations

from contextvars import ContextVar
from threading import Event


class TaskCancelled(RuntimeError):
    """Raised at cooperative cancellation boundaries inside a task."""


current_cancel_event: ContextVar[Event | None] = ContextVar(
    "current_cancel_event",
    default=None,
)


def is_task_cancelled() -> bool:
    event = current_cancel_event.get()
    return event is not None and event.is_set()


def raise_if_task_cancelled() -> None:
    if is_task_cancelled():
        raise TaskCancelled("Task was canceled")
