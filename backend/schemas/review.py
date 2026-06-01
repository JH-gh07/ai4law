from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from backend.schemas.common import ReportArtifact


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReviewTaskStatus(str, Enum):
    """Review pipeline stages, extended to support 8-stage enhanced pipeline."""

    CREATED = "CREATED"
    UPLOADED = "UPLOADED"
    PREPARING = "PREPARING"  # NEW: document classification + scenario extraction
    SEGMENTING = "SEGMENTING"
    CLASSIFYING = "CLASSIFYING"
    MISSING_CHECK = "MISSING_CHECK"  # NEW: global missing‑item detection
    REVIEWING = "REVIEWING"
    CROSS_DOC_CHECK = "CROSS_DOC_CHECK"  # NEW: cross‑document consistency
    AGGREGATING = "AGGREGATING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ClauseType(str, Enum):
    """Clause types — expanded from 6 to 23 for comprehensive coverage.

    Original 6:
      DATA_PROCESSING_SCOPE, CONSENT_NOTICE, SECURITY_MEASURES,
      CROSS_BORDER_TRANSFER, RIGHTS_REQUEST, LIABILITY

    New data‑governance:
      DATA_MINIMIZATION, PURPOSE_LIMITATION, RETENTION_DELETION, DATA_ACCURACY

    New process types:
      THIRD_PARTY_SHARING, ENTRUSTED_PROCESSING, AUTOMATED_DECISION,
      SENSITIVE_PI, MINOR_PROTECTION

    New security / operational:
      INCIDENT_RESPONSE, DATA_BREACH_NOTIFICATION, DPIA_OBLIGATION, DPO_APPOINTMENT

    New SCC‑specific:
      ONWARD_TRANSFER, GOVERNMENT_ACCESS, SUPPLEMENTARY_MEASURES

    Fallback:
      OTHER
    """

    # Original 6
    DATA_PROCESSING_SCOPE = "DATA_PROCESSING_SCOPE"
    CONSENT_NOTICE = "CONSENT_NOTICE"
    SECURITY_MEASURES = "SECURITY_MEASURES"
    CROSS_BORDER_TRANSFER = "CROSS_BORDER_TRANSFER"
    RIGHTS_REQUEST = "RIGHTS_REQUEST"
    LIABILITY = "LIABILITY"
    # New — data governance
    DATA_MINIMIZATION = "DATA_MINIMIZATION"
    PURPOSE_LIMITATION = "PURPOSE_LIMITATION"
    RETENTION_DELETION = "RETENTION_DELETION"
    DATA_ACCURACY = "DATA_ACCURACY"
    # New — process
    THIRD_PARTY_SHARING = "THIRD_PARTY_SHARING"
    ENTRUSTED_PROCESSING = "ENTRUSTED_PROCESSING"
    AUTOMATED_DECISION = "AUTOMATED_DECISION"
    SENSITIVE_PI = "SENSITIVE_PI"
    MINOR_PROTECTION = "MINOR_PROTECTION"
    # New — security / operational
    INCIDENT_RESPONSE = "INCIDENT_RESPONSE"
    DATA_BREACH_NOTIFICATION = "DATA_BREACH_NOTIFICATION"
    DPIA_OBLIGATION = "DPIA_OBLIGATION"
    DPO_APPOINTMENT = "DPO_APPOINTMENT"
    # New — SCC‑specific
    ONWARD_TRANSFER = "ONWARD_TRANSFER"
    GOVERNMENT_ACCESS = "GOVERNMENT_ACCESS"
    SUPPLEMENTARY_MEASURES = "SUPPLEMENTARY_MEASURES"
    # Fallback
    OTHER = "OTHER"


class ReviewSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReviewMethod(str, Enum):
    LLM = "llm"
    RULE = "rule"
    HYBRID = "hybrid"


class ReviewDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class DocumentType(str, Enum):
    PRIVACY_POLICY = "privacy_policy"
    SCC_CONTRACT = "scc_contract"
    DPA = "dpa"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Document understanding
# ---------------------------------------------------------------------------


class DocumentClassification(BaseModel):
    """Result of document type classification."""

    document_type: DocumentType = Field(default=DocumentType.OTHER)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    detected_jurisdiction: str = "cn"
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Extracted metadata: title, version, effective_date, publisher, ...",
    )


class ReviewScenarioContext(BaseModel):
    """Business context merged from user input and auto‑extraction."""

    company_name: str | None = None
    document_title: str | None = None
    document_version: str | None = None
    publisher_entity: str | None = None
    receiver_name: str | None = None
    receiver_country: str | None = None
    transfer_purpose: str | None = None
    pii_count: int = 0
    spi_count: int = 0
    has_scc_draft: bool = False
    industry: str | None = None
    review_focus: str | None = None
    # Auto‑extracted during document understanding
    auto_document_type: DocumentType | None = None
    auto_extracted_facts: dict[str, str] = Field(
        default_factory=dict,
        description="Machine‑extracted facts: data_categories, cross_border_indicators, ...",
    )
    cross_border_indicators: list[str] = Field(default_factory=list)
    uncertain_facts: list[str] = Field(default_factory=list)


class ReviewTaskConfig(BaseModel):
    """User‑selected review depth and options."""

    review_depth: ReviewDepth = ReviewDepth.STANDARD
    target_jurisdiction: str = "cn"
    focus_clause_types: list[str] | None = None
    max_llm_clauses: int = Field(default=20, ge=0, le=100)
    enable_cross_document_check: bool = False
    output_language: str = "zh"


# ---------------------------------------------------------------------------
# Clause models
# ---------------------------------------------------------------------------


class ClausePosition(BaseModel):
    page: int | None = None
    paragraph: int | None = None
    clause_number: str | None = None


class Clause(BaseModel):
    clause_id: str
    file_id: str
    text: str
    heading: str | None = None
    position: ClausePosition = Field(default_factory=ClausePosition)
    # Structural metadata (set by segmenter, used by classifier & reviewer)
    section_hierarchy: list[str] = Field(
        default_factory=list,
        description="e.g. ['Chapter I', 'Article 5']",
    )
    is_table_content: bool = False
    is_appendix_content: bool = False


class ClassifiedClause(Clause):
    # primary type (backward‑compatible)
    clause_type: ClauseType
    matched_keywords: list[str] = Field(default_factory=list)
    # NEW: multi‑label support
    secondary_types: list[ClauseType] = Field(default_factory=list)
    type_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Citation models
# ---------------------------------------------------------------------------


class StructuredCitation(BaseModel):
    """Rich citation with source‑card metadata."""

    source_id: str = ""
    source_title: str = ""  # e.g. "个人信息保护法"
    article: str = ""  # e.g. "第13条"
    snippet: str = ""  # relevant excerpt
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_type: str = Field(
        default="statute",
        description="statute | regulation | standard | guideline | case",
    )
    effective_date: str | None = None


# ---------------------------------------------------------------------------
# Suggested revision
# ---------------------------------------------------------------------------


class SuggestedRevision(BaseModel):
    original_text: str = ""
    suggested_text: str = ""
    revision_rationale: str = ""


# ---------------------------------------------------------------------------
# Review issue (enhanced)
# ---------------------------------------------------------------------------


class ReviewIssue(BaseModel):
    # --- existing fields preserved ---
    issue_id: str
    clause_id: str
    file_id: str
    clause_type: ClauseType
    severity: ReviewSeverity
    title: str
    problem_type: str  # MISSING_REQUIREMENT | AMBIGUOUS_LANGUAGE | NON_COMPLIANT
    risk_analysis: str
    original_excerpt: str
    recommendation: str
    position: ClausePosition = Field(default_factory=ClausePosition)

    # --- backward‑compatible citation field ---
    citation_sources: list[str] = Field(default_factory=list)

    # --- NEW: structured citations ---
    structured_citations: list[StructuredCitation] = Field(default_factory=list)

    # --- NEW: secondary classification ---
    secondary_clause_types: list[ClauseType] = Field(default_factory=list)

    # --- NEW: suggested revision ---
    suggested_revision: SuggestedRevision | None = None

    # --- NEW: uncertainty ---
    facts_uncertain: bool = False
    uncertainty_rationale: str | None = None

    # --- NEW: risk scoring ---
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # --- NEW: review metadata ---
    review_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    review_method: ReviewMethod = ReviewMethod.RULE
    review_depth: ReviewDepth = ReviewDepth.STANDARD


# ---------------------------------------------------------------------------
# Missing item (global completeness check)
# ---------------------------------------------------------------------------


class MissingItem(BaseModel):
    """A globally missing clause / requirement in the document."""

    item_id: str
    clause_type: ClauseType
    title: str
    description: str
    severity: ReviewSeverity = ReviewSeverity.HIGH
    legal_basis: list[str] = Field(default_factory=list)
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Aggregated review (enhanced)
# ---------------------------------------------------------------------------


class AggregatedReview(BaseModel):
    overall_rating: str  # "高风险" | "中风险" | "低风险"
    overall_risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    summary: str
    issues: list[ReviewIssue]
    issue_counts: dict[str, int]
    priority_actions: list[str]

    # NEW
    missing_items: list[MissingItem] = Field(default_factory=list)
    document_profile: dict[str, str] = Field(
        default_factory=dict,
        description="document_type, title, clause_distribution, ...",
    )
    clauses_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Clause type -> count distribution",
    )
    consistency_warnings: list[str] = Field(default_factory=list)
    review_metadata: dict = Field(
        default_factory=dict,
        description="review_started_at, review_mode, model_version, ...",
    )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ReviewTaskCreateResponse(BaseModel):
    id: str
    status: ReviewTaskStatus
    created_at: datetime


class UploadedFileResponse(BaseModel):
    id: str
    task_id: str
    filename: str
    content_type: str


class ReviewTaskStatusResponse(BaseModel):
    id: str
    status: ReviewTaskStatus
    progress: int
    summary: AggregatedReview | None = None


class ReviewAnalyzeResponse(BaseModel):
    id: str
    status: ReviewTaskStatus
    progress: int


class ReviewGenerateRequest(BaseModel):
    uploaded_files: list[str] = Field(default_factory=list, min_length=1)
    # NEW: optional fields from frontend context — all defaulted for backward compat
    document_type: str | None = None  # "privacy_policy" | "scc_contract" | "dpa" | "other"
    review_focus: str | None = None
    scenario_context: ReviewScenarioContext | None = None
    review_config: ReviewTaskConfig | None = None


class ReviewGenerateResponse(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    risk_level: str
    result: dict = Field(default_factory=dict)
    consistency_issues: list[str] = Field(default_factory=list)


class ReviewAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    progress: int
    created_at: datetime
    updated_at: datetime


class ReviewAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    progress: int
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    result: ReviewGenerateResponse | None = None


class ReviewIssuesResponse(BaseModel):
    task_id: str
    issues: list[ReviewIssue]


class ReviewReportResponse(BaseModel):
    report: ReportArtifact
    review: AggregatedReview
