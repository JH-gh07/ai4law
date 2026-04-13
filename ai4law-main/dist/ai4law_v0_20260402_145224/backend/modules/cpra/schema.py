from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CPRAAttachment(BaseModel):
    file_role: Literal["privacy_policy", "rights_sop", "data_map", "vendor_list", "other"]
    file_name: str = Field(min_length=1)
    file_format: Literal["docx", "pdf", "url", "xlsx", "csv"]
    storage_uri: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = None


class CPRARequest(BaseModel):
    business_model: str = Field(min_length=2)
    data_lifecycle: str = Field(min_length=2)
    notice_and_consent: str = Field(min_length=2)
    consumer_rights_process: str = Field(min_length=2)
    opt_out_and_sale_sharing: str = Field(min_length=2)
    vendor_management: str = Field(default="")
    attachments: list[CPRAAttachment] = Field(min_length=1)
    company_name: str = Field(default="示例企业")


class CPRAGapItem(BaseModel):
    domain: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    gap: str
    legal_basis: str
    recommendation: str
    phase: Literal["short_term", "mid_term", "long_term"]


class CPRAChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class CPRAResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    company_name: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    gap_items: list[CPRAGapItem] = Field(default_factory=list)
    chapters: list[CPRAChapter] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    attachment_notes: list[str] = Field(default_factory=list)


class CPRAAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class CPRAAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: CPRAResult | None = None

