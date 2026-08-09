from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CNRecipientEntity(BaseModel):
    entity_name: str = Field(min_length=2)
    country_region: str = Field(min_length=2)
    entity_role: Literal["processor", "controller", "subprocessor", "affiliate", "vendor"]
    is_restricted_party: bool = False


class CNFlowAttachment(BaseModel):
    file_role: Literal["data_inventory", "entity_inventory", "supporting_material"]
    file_name: str = Field(min_length=1)
    file_format: Literal["xlsx", "csv", "docx", "pdf"]
    storage_uri: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = None


class CNFlowRequest(BaseModel):
    transfer_purpose: str = Field(min_length=2)
    data_categories: list[str] = Field(min_length=1)
    sensitive_data_flags: list[str] = Field(default_factory=list)
    recipient_entities: list[CNRecipientEntity] = Field(min_length=1)
    transfer_chain: str = Field(min_length=2)
    attachments: list[CNFlowAttachment] = Field(min_length=2)
    company_name: str = Field(default="示例企业")
    us_person_count: int | None = Field(default=None, ge=0)
    transaction_type: str | None = None
    doj_data_category_by_item: dict[str, str] = Field(default_factory=dict)


class CNFlowRiskItem(BaseModel):
    risk_id: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    title: str
    basis: str
    recommendation: str
    affected_entities: list[str] = Field(default_factory=list)


class CNFlowChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class CNFlowResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    company_name: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    risk_items: list[CNFlowRiskItem] = Field(default_factory=list)
    chapters: list[CNFlowChapter] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    attachment_notes: list[str] = Field(default_factory=list)


class CNFlowAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class CNFlowAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: CNFlowResult | None = None
