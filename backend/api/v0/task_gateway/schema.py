from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class APIEnvelope(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any


class V0TaskCreateRequest(BaseModel):
    module_code: Literal["2.2", "2.3", "3.2", "3.3", "3.4", "4.1", "4.2"] = Field(
        description="v0 currently supports 2.2/2.3/3.2/3.3/3.4/4.1/4.2"
    )
    session_id: str = Field(min_length=1)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    attachment_ids: list[str] = Field(default_factory=list)


class V0TaskCreateData(BaseModel):
    task_id: str
    module_code: str
    status: str


class V0TaskStatusData(BaseModel):
    task_id: str
    module_code: str
    status: str
    progress: int
    stage: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None


class V0ArtifactItem(BaseModel):
    artifact_id: str
    file_name: str
    file_type: str
    file_path: str
    download_url: str


class V0TaskArtifactsData(BaseModel):
    task_id: str
    module_code: str
    artifacts: list[V0ArtifactItem] = Field(default_factory=list)


class V0UploadedFileData(BaseModel):
    file_id: str
    file_name: str
    mime: str
    size: int
    path: str
    uploaded_at: datetime


class V0RuleHit(BaseModel):
    rule_id: str
    hit: Literal["pass", "warn", "fail"]
    evidence: str


class V0TaskAuditData(BaseModel):
    task_id: str
    module_code: str
    status: str
    stage: str
    summary: str
    input_digest: str | None = None
    rule_hits: list[V0RuleHit] = Field(default_factory=list)
    retrieval_sources: list[str] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    model_version: str = "v0-local"
    template_version: str = "v0"
