from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TIAAttachment(BaseModel):
    file_role: Literal["transfer_agreement", "country_law_analysis", "technical_control_doc", "other"]
    file_name: str = Field(min_length=1)
    file_format: Literal["docx", "pdf"]
    storage_uri: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = None


class TIARequest(BaseModel):
    transfer_tool: Literal["scc", "bcr", "derogation"]
    data_exporter_profile: str = Field(min_length=2)
    data_importer_profile: str = Field(min_length=2)
    third_country_assessment: str = Field(min_length=2)
    supplementary_measures: str = Field(min_length=2)
    final_conclusion: str = Field(min_length=2)
    attachments: list[TIAAttachment] = Field(min_length=1)


class TIAChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class TIAResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    transfer_tool: str
    risk_level: str
    chapters: list[TIAChapter]
    consistency_issues: list[str]
    attachment_notes: list[str] = Field(default_factory=list)


class TIAAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class TIAAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: TIAResult | None = None

