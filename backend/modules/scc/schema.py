from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ── Enum types ──

class LegalBasis(str, Enum):
    consent = "consent"
    contract_necessity = "contract_necessity"
    hr_management = "hr_management"
    legal_obligation = "legal_obligation"
    vital_interest = "vital_interest"
    public_interest = "public_interest"
    other = "other"


class ReceiverType(str, Enum):
    subsidiary = "subsidiary"
    parent = "parent"
    affiliate = "affiliate"
    third_party_processor = "third_party_processor"
    third_party_controller = "third_party_controller"
    certification_body = "certification_body"
    other = "other"


class DataProcessingMethod(str, Enum):
    plaintext = "plaintext"
    hashed = "hashed"
    masked = "masked"
    anonymized = "anonymized"
    aggregated = "aggregated"
    encrypted = "encrypted"
    other = "other"


PathType = Literal["security_assessment", "standard_contract", "certification", "exemption", "uncertain"]
EvidenceStrength = Literal["user_claim_only", "partial_evidence", "documented_evidence", "verified_evidence"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "BLOCKER"]


# ── Field-level data classification ──

class DataFieldItem(BaseModel):
    """Single data field for classification agent."""
    field_name: str = Field(min_length=1)
    field_description: str = ""
    sample_value: str = ""
    user_pii_label: str = ""  # "personal_information" | "not_personal_information" | "sensitive_personal_information"
    user_spi_label: str = ""
    processing_method: DataProcessingMethod = DataProcessingMethod.plaintext
    business_purpose: str = ""
    related_fields: list[str] = Field(default_factory=list)


class DataFieldClassification(BaseModel):
    """Agent output per field."""
    field_name: str
    user_claim: str
    agent_judgment: Literal[
        "personal_information", "not_personal_information",
        "sensitive_personal_information", "potential_personal_information",
        "potential_sensitive_personal_information",
    ]
    risk: RiskLevel = RiskLevel.LOW
    reason: str = ""
    required_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


# ── Path diagnosis ──

class PathDiagnosisInput(BaseModel):
    company_name: str
    is_ciio: bool = False
    has_important_data: bool = False
    pii_count: int = Field(default=0, ge=0)
    spi_count: int = Field(default=0, ge=0)
    transfer_purpose: str = ""
    legal_basis: list[LegalBasis] = Field(default_factory=list)
    receiver_type: ReceiverType = ReceiverType.other
    receiver_country: str = ""
    industry: str = ""
    is_hr_management: bool = False
    is_certification_body: bool = False
    has_scc_draft: bool = False
    has_certification_material: bool = False
    has_exemption_material: bool = False


class PathDiagnosisResult(BaseModel):
    recommended_path: PathType
    alternative_path: PathType | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""
    blocking_issues: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    triggered_thresholds: list[str] = Field(default_factory=list)
    exemption_assessment: str = ""


# ── Legal basis review ──

class LegalBasisReviewItem(BaseModel):
    legal_basis: str
    status: Literal["supported", "weak", "insufficient_evidence", "not_recommended"]
    reason: str = ""
    recommended_adjustment: str = ""
    required_evidence: list[str] = Field(default_factory=list)
    evidence_found: list[str] = Field(default_factory=list)
    evidence_missing: list[str] = Field(default_factory=list)


# ── Contract review ──

class ContractFinding(BaseModel):
    finding_id: str = Field(min_length=1)
    location: str = ""
    issue: str = ""
    severity: RiskLevel = RiskLevel.MEDIUM
    risk_analysis: str = ""
    suggested_text: str = ""
    clause_category: str = ""


# ── Evidence verification ──

class EvidenceVerificationItem(BaseModel):
    claim: str
    evidence_status: EvidenceStrength = "user_claim_only"
    supporting_material: list[str] = Field(default_factory=list)
    gap: str = ""
    report_strategy: str = ""


# ── RAG planning ──

class RAGQueryPlan(BaseModel):
    issue: str
    queries: list[str] = Field(default_factory=list)
    required_source_types: list[str] = Field(default_factory=list)


# ── Report review ──

class ReportReviewProblem(BaseModel):
    type: Literal[
        "unsupported_positive_claim",
        "missing_risk_item",
        "inconsistent_rating",
        "irrelevant_citation",
        "template_incomplete",
        "concept_confusion",
    ]
    text: str = ""
    reason: str = ""
    repair: str = ""


class ReportReviewResult(BaseModel):
    review_status: Literal["pass", "needs_repair", "blocked"]
    problems: list[ReportReviewProblem] = Field(default_factory=list)


# ── Clarification ──

class ClarificationQuestion(BaseModel):
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    question: str
    why: str


class ClarificationResult(BaseModel):
    questions: list[ClarificationQuestion] = Field(default_factory=list)


# ── Explanation ──

class ExplanationSegment(BaseModel):
    step_label: str
    description: str
    source: str = ""


class ExplanationResult(BaseModel):
    summary: str = ""
    segments: list[ExplanationSegment] = Field(default_factory=list)


# ── Core request / profile ──

class SCCRequest(BaseModel):
    """Enriched CN SCC request supporting all agent inputs."""
    company_name: str = Field(min_length=2)
    receiver_name: str = Field(min_length=2)
    receiver_country: str = Field(min_length=2)
    transfer_purpose: str = Field(min_length=2)
    pii_count: int = Field(default=0, ge=0)
    spi_count: int = Field(default=0, ge=0)
    has_scc_draft: bool = False
    uploaded_files: list[str] = Field(default_factory=list)

    # Extended fields for agent system
    is_ciio: bool = False
    has_important_data: bool = False
    legal_basis: list[LegalBasis] = Field(default_factory=list)
    receiver_type: ReceiverType = ReceiverType.other
    industry: str = ""
    is_hr_management: bool = False
    is_certification_body: bool = False
    has_certification_material: bool = False
    has_exemption_material: bool = False

    # Field-level data
    data_fields: list[DataFieldItem] = Field(default_factory=list)

    # User-provided evidence summaries
    contract_summary: str = ""
    privacy_policy_summary: str = ""
    employee_handbook_summary: str = ""
    collective_agreement_summary: str = ""
    consent_record_summary: str = ""
    legal_basis_argument: str = ""


class SCCProfile(BaseModel):
    company_name: str
    receiver_name: str
    receiver_country: str
    transfer_purpose: str
    pii_count: int
    spi_count: int
    has_scc_draft: bool
    is_ciio: bool = False
    has_important_data: bool = False
    legal_basis: list[LegalBasis] = Field(default_factory=list)
    receiver_type: ReceiverType = ReceiverType.other
    industry: str = ""
    is_hr_management: bool = False
    is_certification_body: bool = False
    has_certification_material: bool = False
    has_exemption_material: bool = False
    extracted_notes: list[str] = Field(default_factory=list)
    attachment_texts: dict[str, str] = Field(default_factory=dict)


class SCCChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class SCCResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    profile: SCCProfile
    chapters: list[SCCChapter]
    consistency_issues: list[str]

    # Agent enrichment
    path_diagnosis: PathDiagnosisResult | None = None
    field_classifications: list[DataFieldClassification] = Field(default_factory=list)
    legal_basis_reviews: list[LegalBasisReviewItem] = Field(default_factory=list)
    contract_findings: list[ContractFinding] = Field(default_factory=list)
    evidence_verifications: list[EvidenceVerificationItem] = Field(default_factory=list)
    report_review: ReportReviewResult | None = None
    clarification: ClarificationResult | None = None
    explanation: ExplanationResult | None = None
    facts: list[dict] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)
    evidence_chain: list[dict] = Field(default_factory=list)
    rag_query_plans: list[RAGQueryPlan] = Field(default_factory=list)
    trace_manifest_path: str = ""


class SCCAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class SCCAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: SCCResult | None = None
