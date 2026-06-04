from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class CopilotTaskSpace(BaseModel):
    id: str
    name: str
    jurisdiction: str
    module: str
    mode: str | None = None
    workspace_style: str | None = None


class CopilotContext(BaseModel):
    current_step: str | None = None
    blocker: str | None = None
    runs_count: int = 0
    issues_count: int = 0
    evidence_count: int = 0
    artifact_count: int = 0
    top_issues: list[str] = Field(default_factory=list)
    latest_artifacts: list[str] = Field(default_factory=list)
    trace_summary: str | None = None
    trace_stage: str | None = None
    trace_status: Literal["idle", "running", "completed", "failed"] | None = None
    trace_highlights: list[str] = Field(default_factory=list)


class CopilotChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    action: str | None = None
    task_space: CopilotTaskSpace
    context: CopilotContext = Field(default_factory=CopilotContext)
    messages: list[CopilotMessage] = Field(default_factory=list)


class CopilotChatResponse(BaseModel):
    reply: str
    model: str
    enabled: bool
    fallback: bool = False
