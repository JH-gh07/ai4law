from __future__ import annotations

from contextvars import ContextVar

from backend.common.trace.recorder import TraceRecorder


current_trace: ContextVar[TraceRecorder | None] = ContextVar("current_trace", default=None)

