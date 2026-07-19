"""BCR module schemas — extended for document-driven review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---- enumerations ----

BCRCode = Literal[
    "3.2-C1", "3.2-C2", "3.2-C3", "3.2-C4", "3.2-C5",
    "3.2-C6", "3.2-C7", "3.2-C8", "3.2-C9", "3.2-C10",
]
BCRScore = Literal["compliant", "partial", "non_compliant"]

BCRDocumentRole = Literal[
    "main_bcr_document",
    "member_list",
    "internal_binding_agreement",
    "complaint_procedure",
    "audit_training_policy",
    "tia_document",
    "government_access_policy",
    "other_attachment",
]

BCRTypeLabel = Literal["BCR-C", "BCR-P", "unknown"]
BCRConsistency = Literal["consistent", "mismatch", "uncertain"]
BCRRating = Literal["基本合规", "部分缺失", "高风险"]
BCRRiskLevel = Literal["HIGH", "MEDIUM", "LOW"]
BCRReviewDepth = Literal["quick", "standard", "deep"]

# ---- form‑driven models (preserved for backward compat) ----

class BCRReviewItem(BaseModel):
    code: BCRCode
    title: str = Field(min_length=2)
    score: BCRScore
    finding: str = Field(min_length=2)
    legal_basis: str = Field(min_length=2)
    recommendation: str = Field(min_length=2)
    evidence: str = ""


class BCRAttachment(BaseModel):
    file_name: str = Field(min_length=1)
    file_format: Literal["pdf", "docx"]
    storage_uri: str = Field(min_length=1)


# ---- document‑driven models (new) ----

class BCRUploadedDocument(BaseModel):
    file_id: str
    file_name: str
    file_type: str  # pdf / docx / txt / md
    file_path: str
    document_role: BCRDocumentRole = "other_attachment"
    auto_detected_role: bool = False


class BCRTypeClassification(BaseModel):
    declared_bcr_type: BCRTypeLabel = "unknown"
    actual_bcr_type: BCRTypeLabel = "unknown"
    type_consistency: BCRConsistency = "uncertain"
    risk_level: BCRRiskLevel = "MEDIUM"
    evidence: list[str] = Field(default_factory=list)
    recommendation: str = ""


class BCRScenarioContext(BaseModel):
    company_name: str | None = None
    headquarters_country: str | None = None
    declared_bcr_type: str | None = None
    eu_liable_entity: str | None = None
    lead_supervisory_authority: str | None = None
    processes_on_behalf_of_clients: bool | None = None
    third_countries: list[str] = Field(default_factory=list)
    auto_extracted_facts: dict[str, str] = Field(default_factory=dict)


class BCRReviewConfig(BaseModel):
    review_depth: BCRReviewDepth = "standard"
    max_llm_clauses: int = Field(default=20, ge=0, le=100)
    enable_cross_document_check: bool = False


class BCRFinding(BaseModel):
    finding_id: str
    requirement_id: str
    location: str = ""
    clause_excerpt: str = ""
    title: str
    risk_level: BCRRiskLevel
    risk_score: float = 0.0
    finding: str
    legal_basis: list[str] = Field(default_factory=list)
    recommendation: str = ""
    suggested_revision: str | None = None
    facts_uncertain: bool = False
    review_confidence: float = 0.85


# ---- request / response ----

class BCRRequest(BaseModel):
    company_name: str = Field(min_length=2)
    # form‑driven (optional now — backward compat)
    review_items: list[BCRReviewItem] = Field(default_factory=list)
    attachments: list[BCRAttachment] = Field(default_factory=list)
    uploaded_files: list[str] = Field(default_factory=list)
    # document‑driven (new)
    uploaded_documents: list[BCRUploadedDocument] = Field(default_factory=list)
    scenario_context: BCRScenarioContext | None = None
    review_config: BCRReviewConfig | None = None


class BCRProblem(BaseModel):
    code: BCRCode
    title: str
    risk_level: BCRRiskLevel
    finding: str
    legal_basis: str
    recommendation: str
    evidence: str = ""


class BCRChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class BCRResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    company_name: str
    rating: BCRRating
    problems: list[BCRProblem] = Field(default_factory=list)
    chapters: list[BCRChapter] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    attachment_notes: list[str] = Field(default_factory=list)
    # document‑driven (new)
    bcr_type_classification: BCRTypeClassification | None = None
    findings: list[BCRFinding] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    review_metadata: dict = Field(default_factory=dict)


class BCRAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class BCRAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: BCRResult | None = None
