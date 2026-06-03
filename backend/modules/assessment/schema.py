from typing import Literal

from pydantic import BaseModel, Field

from backend.modules.assessment.task_state import AssessmentTaskState

PathCheckMode = Literal["generate_only", "warn_only", "block_on_mismatch"]
IssueCertainty = Literal["confirmed_issue", "suspected_issue", "default_review_item"]


# ═══════════════════════════════════════════════════════════════════════
# Structured input sub-models — official template aligned
# ═══════════════════════════════════════════════════════════════════════

class DataInventoryItem(BaseModel):
    """Field-level data inventory item for official self-assessment report."""
    name: str = Field(min_length=1, description="数据项名称")
    description: str = ""
    data_subject: str = ""
    personal_info_type: str = ""  # personal_information | sensitive_personal_information | important_data | general
    is_important_data_candidate: bool = False
    necessity: str = ""
    example: str = ""
    volume: str = ""
    retention_period: str = ""
    remarks: str = ""


class RecipientInfo(BaseModel):
    """Structured overseas recipient information."""
    name: str = Field(min_length=1)
    country_or_region: str = ""
    role: str = ""  # 境外接收方 | 实际处理者 | 子处理者
    relationship: str = ""  # 母公司/子公司/合作方/供应商
    security_certifications: list[str] = Field(default_factory=list)
    audit_reports: list[str] = Field(default_factory=list)
    legal_environment_summary: str = ""
    processing_purpose: str = ""
    processing_method: str = ""
    storage_location: str = ""


class DownstreamProcessor(BaseModel):
    """Actual downstream processor (may differ from declared recipient)."""
    name: str = Field(min_length=1)
    country_or_region: str = ""
    role: str = ""  # sub_processor | actual_processor
    processing_activity: str = ""
    contract_covered: bool = False
    onward_transfer_constraint: str = ""


class LegalDocumentReview(BaseModel):
    """Legal document clause coverage review (6 core clauses per Assessment Measures Art.9)."""
    document_name: str = ""
    clause_coverage: dict[str, str] = Field(default_factory=lambda: {
        "purpose_method_scope": "unchecked",
        "overseas_retention_location_period": "unchecked",
        "onward_transfer_constraint": "unchecked",
        "legal_environment_change_response": "unchecked",
        "breach_liability_dispute_resolution": "unchecked",
        "incident_response_and_individual_rights": "unchecked",
    })
    raw_clause_refs: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    risk_level: str = "MEDIUM"


class SecurityCapability(BaseModel):
    """Data security capability information."""
    management_measures: list[str] = Field(default_factory=list)
    technical_measures: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    compliance_records: list[str] = Field(default_factory=list)


class ComplianceHistory(BaseModel):
    """Historical compliance record."""
    has_penalty: bool = False
    penalty_time: str = ""
    penalty_reason: str = ""
    rectification_status: str = ""


class PersonalInfoProtection(BaseModel):
    """Personal information protection measures."""
    separate_consent_status: str = ""  # obtained | partial | missing
    notice_content: str = ""
    rights_response: str = ""
    archive_evidence: str = ""


class SystemLink(BaseModel):
    """System link and transfer chain information."""
    domestic_systems: list[str] = Field(default_factory=list)
    transfer_links: list[str] = Field(default_factory=list)
    transit_locations: list[str] = Field(default_factory=list)
    overseas_systems: list[str] = Field(default_factory=list)


class SelfAssessmentInfo(BaseModel):
    """Self-assessment work information."""
    start_date: str = ""
    end_date: str = ""
    participating_departments: list[str] = Field(default_factory=list)
    preliminary_conclusion: str = ""


# ═══════════════════════════════════════════════════════════════════════
# Main models
# ═══════════════════════════════════════════════════════════════════════

class AssessmentRequest(BaseModel):
    # ── Original fields ──
    company_name: str = Field(min_length=2)
    industry: str = Field(default="")
    is_ciio: bool = False
    contains_important_data: bool = False
    pii_count: int = Field(default=0, ge=0)
    spi_count: int = Field(default=0, ge=0)
    transfer_purpose: str = Field(min_length=2)
    receiver_country: str = Field(min_length=2)
    force_override_path: bool = False
    uploaded_files: list[str] = Field(default_factory=list)
    path_check_mode: PathCheckMode = "warn_only"

    # ── New structured fields — official template aligned ──
    self_assessment_info: SelfAssessmentInfo | None = None
    data_inventory_items: list[DataInventoryItem] = Field(default_factory=list)
    recipient_info: RecipientInfo | None = None
    downstream_processors: list[DownstreamProcessor] = Field(default_factory=list)
    legal_document_review: LegalDocumentReview | None = None
    security_capability: SecurityCapability | None = None
    compliance_history: ComplianceHistory | None = None
    personal_info_protection: PersonalInfoProtection | None = None
    system_link: SystemLink | None = None


class CompanyProfile(BaseModel):
    company_name: str
    industry: str
    is_ciio: bool
    contains_important_data: bool
    pii_count: int
    spi_count: int
    transfer_purpose: str
    receiver_country: str
    extracted_notes: list[str] = Field(default_factory=list)
    attachment_metadata: list[dict] = Field(default_factory=list)
    # ── Carried from structured request fields ──
    data_inventory_items: list[DataInventoryItem] = Field(default_factory=list)
    recipient_info: RecipientInfo | None = None
    downstream_processors: list[DownstreamProcessor] = Field(default_factory=list)
    legal_document_review: LegalDocumentReview | None = None
    security_capability: SecurityCapability | None = None
    compliance_history: ComplianceHistory | None = None
    personal_info_protection: PersonalInfoProtection | None = None
    system_link: SystemLink | None = None
    self_assessment_info: SelfAssessmentInfo | None = None


class RegulationHit(BaseModel):
    source_id: str
    title: str
    article: str
    snippet: str


class ChapterContent(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str
    footnote_map: dict | None = None


class AssessmentResult(BaseModel):
    task_id: str
    state: AssessmentTaskState
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    profile: CompanyProfile
    regulations: list[RegulationHit]
    chapters: list[ChapterContent]
    consistency_issues: list[str]


class AssessmentAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class AssessmentAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: AssessmentResult | None = None
