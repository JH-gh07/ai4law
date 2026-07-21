from __future__ import annotations

from contextvars import ContextVar
from typing import Any


current_llm_client: ContextVar[Any | None] = ContextVar(
    "current_llm_client",
    default=None,
)
