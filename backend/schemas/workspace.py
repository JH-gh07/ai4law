from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceStatePayload(BaseModel):
    task_spaces: list[dict] = Field(default_factory=list)
    module_runs: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    evidence_hits: list[dict] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)


class WorkspaceStateResponse(BaseModel):
    state: WorkspaceStatePayload
    updated_at: datetime
