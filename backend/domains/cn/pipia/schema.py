from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PIPIACompanyProfile(BaseModel):
    company_name: str = Field(min_length=2)
    company_uscc: str = Field(min_length=8)
    is_ciio: bool = False
    processing_person_count: int = Field(default=0, ge=0)
    outbound_pi_count: int = Field(default=0, ge=0)
    outbound_spi_count: int = Field(default=0, ge=0)
    industry: str = Field(default="")


class PIPIATransferContext(BaseModel):
    purpose: str = Field(min_length=2)
    recipient_name: str = Field(min_length=2)
    recipient_country_region: str = Field(min_length=2)
    legal_basis: str = Field(min_length=2)


class PIPIAPersonalInfoScope(BaseModel):
    pi_categories: list[str] = Field(min_length=1)
    spi_categories: list[str] = Field(default_factory=list)
    subject_volume: int = Field(default=0, ge=0)


class PIPIARightsProtection(BaseModel):
    notice_mechanism: str = Field(min_length=2)
    consent_mechanism: str = Field(min_length=2)
    dsar_channel: str = Field(min_length=2)
    retention_policy: str = Field(min_length=2)


class PIPIAEmergencyPlan(BaseModel):
    incident_response_sla_hours: int = Field(ge=1, le=168)
    escalation_path: str = Field(min_length=2)


class PIPIAAttachment(BaseModel):
    file_role: Literal["scc_contract", "certification_material", "internal_policy", "supporting_evidence"]
    file_name: str = Field(min_length=1)
    file_format: Literal["doc", "docx", "pdf", "txt", "md", "json", "csv"]
    storage_uri: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = None


class PIPIARequest(BaseModel):
    route_type: Literal["certification", "scc_filing", "hr_exemption"]
    company_profile: PIPIACompanyProfile
    transfer_context: PIPIATransferContext
    personal_info_scope: PIPIAPersonalInfoScope
    rights_protection: PIPIARightsProtection
    emergency_plan: PIPIAEmergencyPlan
    attachments: list[PIPIAAttachment] = Field(min_length=1)


class PIPIAChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class PIPIAFilingReadiness(BaseModel):
    status: Literal["ready", "supplement_required", "blocked"]
    reason: str = ""
    blocking_items: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class PIPIAResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    route_type: str
    risk_level: str
    chapters: list[PIPIAChapter]
    consistency_issues: list[str]
    attachment_notes: list[str] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)
    evidence_chain: list[dict] = Field(default_factory=list)
    material_gaps: list[str] = Field(default_factory=list)
    filing_readiness: PIPIAFilingReadiness


class PIPIAAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class PIPIAAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: PIPIAResult | None = None
