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


class PIPIAPathEvidence(BaseModel):
    recipient_notice_complete: bool | None = None
    sensitive_information_classification_confirmed: bool | None = None
    consent_evidence_complete: bool | None = None
    scc_required_clauses_complete: bool | None = None
    hr_rules_lawfully_adopted: bool | None = None
    employee_handbook_has_explicit_cross_border_terms: bool | None = None
    collective_agreement_has_explicit_cross_border_terms: bool | None = None
    recipient_privacy_policy_provided: bool | None = None
    certification_body_china_recognized: bool | None = None
    certification_legal_obligation_citation_provided: bool | None = None
    contract_governing_law: str = ""
    contract_exclusive_jurisdiction: str = ""
    china_data_subject_rights_terms_present: bool | None = None


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
    path_evidence: PIPIAPathEvidence = Field(default_factory=PIPIAPathEvidence)
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
    legal_basis: list[str] = Field(default_factory=list)
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
