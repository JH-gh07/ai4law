"""RunEvent — 前端消费的运行时事件模型，与 TraceEvent（审计文件）并行。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

EventType = Literal[
    "status",
    "thought",
    "tool_start",
    "tool_result",
    "intermediate",
    "warning",
    "final",
    "final_brief",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    seq: int = 0
    event_type: EventType
    timestamp: str = Field(default_factory=_utc_now_iso)
    summary: str = ""
    detail: dict[str, Any] | None = None
    level: Literal["audit", "debug"] = "audit"
