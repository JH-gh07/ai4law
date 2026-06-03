from __future__ import annotations

from contextvars import ContextVar

from backend.common.trace.recorder import TraceRecorder

from backend.common.events.manager import SSEManager


current_trace: ContextVar[TraceRecorder | None] = ContextVar("current_trace", default=None)

current_ssemanager: ContextVar[SSEManager | None] = ContextVar("current_ssemanager", default=None)

