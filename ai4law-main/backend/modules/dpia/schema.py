from __future__ import annotations

from pydantic import BaseModel, Field


class DPIAAttachment(BaseModel):
    file_role: str = Field(pattern=r"^(data_flow_diagram|security_policy|dpa|other)$")
    file_name: str = Field(min_length=1)
    file_format: str = Field(pattern=r"^(docx|pdf|png|jpg)$")
    storage_uri: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = None


class DPIARequest(BaseModel):
    project_name: str = Field(min_length=2)
    processing_description: str = Field(min_length=2)
    purpose_and_necessity: str = Field(min_length=2)
    lawful_basis: str = Field(min_length=2)
    risk_assessment: str = Field(min_length=2)
    mitigation_measures: str = Field(min_length=2)
    residual_risk: str = Field(min_length=2)
    attachments: list[DPIAAttachment] = Field(default_factory=list)


class DPIAChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class DPIAResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    project_name: str
    risk_level: str
    chapters: list[DPIAChapter]
    consistency_issues: list[str]
    attachment_notes: list[str] = Field(default_factory=list)


class DPIAAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class DPIAAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: DPIAResult | None = None

