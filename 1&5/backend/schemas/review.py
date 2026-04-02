from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from backend.schemas.common import ReportArtifact


class ReviewTaskStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    SEGMENTING = "SEGMENTING"
    CLASSIFYING = "CLASSIFYING"
    REVIEWING = "REVIEWING"
    AGGREGATING = "AGGREGATING"
    PLANNING = "PLANNING"
    REWRITING = "REWRITING"
    RECOMPOSING = "RECOMPOSING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewMode(str, Enum):
    REPORT = "REPORT"
    REDLINE = "REDLINE"


class ContractType(str, Enum):
    GENERAL_CONTRACT = "GENERAL_CONTRACT"
    PERSONAL_INFO_SCC = "PERSONAL_INFO_SCC"
    DATA_PROCESSING_AGREEMENT = "DATA_PROCESSING_AGREEMENT"
    PRIVACY_POLICY = "PRIVACY_POLICY"


class ReviewStance(str, Enum):
    PARTY_A = "PARTY_A"
    PARTY_B = "PARTY_B"


class SectionType(str, Enum):
    BODY = "BODY"
    APPENDIX = "APPENDIX"
    TABLE = "TABLE"
    TITLE = "TITLE"


class ClauseType(str, Enum):
    DEFINITIONS = "DEFINITIONS"
    DATA_PROCESSING_SCOPE = "DATA_PROCESSING_SCOPE"
    CONSENT_NOTICE = "CONSENT_NOTICE"
    SECURITY_MEASURES = "SECURITY_MEASURES"
    THIRD_PARTY_SHARING = "THIRD_PARTY_SHARING"
    CROSS_BORDER_TRANSFER = "CROSS_BORDER_TRANSFER"
    RIGHTS_REQUEST = "RIGHTS_REQUEST"
    LIABILITY = "LIABILITY"
    DISPUTE_RESOLUTION = "DISPUTE_RESOLUTION"
    PIA_FILING = "PIA_FILING"
    APPENDIX = "APPENDIX"
    OTHER = "OTHER"


class PartyBias(str, Enum):
    NEUTRAL = "NEUTRAL"
    PARTY_A_FAVORABLE = "PARTY_A_FAVORABLE"
    PARTY_B_FAVORABLE = "PARTY_B_FAVORABLE"


class ReviewSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RevisionAction(str, Enum):
    RETAIN = "RETAIN"
    MODIFY = "MODIFY"
    REWRITE = "REWRITE"
    INSERT_AFTER = "INSERT_AFTER"
    APPEND_APPENDIX = "APPEND_APPENDIX"


class CustomRuleInput(BaseModel):
    ids: list[str] = Field(default_factory=list)
    text: str = ""


class ClausePosition(BaseModel):
    page: int | None = None
    paragraph: int | None = None
    clause_number: str | None = None
    section_path: str | None = None


class Clause(BaseModel):
    clause_id: str
    file_id: str
    text: str
    heading: str | None = None
    section_type: SectionType = SectionType.BODY
    appendix_id: str | None = None
    position: ClausePosition = Field(default_factory=ClausePosition)


class ClassifiedClause(Clause):
    clause_type: ClauseType
    matched_keywords: list[str] = Field(default_factory=list)
    party_bias: PartyBias = PartyBias.NEUTRAL


class ReviewIssue(BaseModel):
    issue_id: str
    clause_id: str
    file_id: str
    clause_type: ClauseType
    severity: ReviewSeverity
    title: str
    problem_type: str
    risk_analysis: str
    original_excerpt: str
    citation_sources: list[str]
    recommendation: str
    stance_relevance: str = ""
    suggested_revision: str | None = None
    position: ClausePosition = Field(default_factory=ClausePosition)


class AggregatedReview(BaseModel):
    overall_rating: str
    summary: str
    issues: list[ReviewIssue]
    issue_counts: dict[str, int]
    priority_actions: list[str]


class ReviewReport(BaseModel):
    title: str
    file_overview: list[str]
    legal_basis: list[str]
    overall_rating: str
    executive_summary: str
    issues: list[ReviewIssue]
    priority_actions: list[str]


class RevisionInstruction(BaseModel):
    clause_id: str
    action: RevisionAction
    reason: str
    issue_ids: list[str] = Field(default_factory=list)
    target_section_type: SectionType = SectionType.BODY
    appendix_id: str | None = None


class RevisedClause(BaseModel):
    clause_id: str
    heading: str | None = None
    revised_text: str
    revision_reason: str
    action: RevisionAction
    section_type: SectionType = SectionType.BODY
    appendix_id: str | None = None


class RevisionDiffItem(BaseModel):
    clause_id: str
    heading: str | None = None
    original_text: str
    revised_text: str
    reason: str
    severity: ReviewSeverity | None = None
    action: RevisionAction


class ReviewWorkspace(BaseModel):
    task_id: str
    review_mode: ReviewMode
    contract_type: ContractType
    review_stance: ReviewStance
    custom_rules: CustomRuleInput = Field(default_factory=CustomRuleInput)
    source_filenames: list[str] = Field(default_factory=list)
    clause_count: int = 0
    appendix_count: int = 0


class ReviewTaskCreateRequest(BaseModel):
    review_mode: ReviewMode = ReviewMode.REPORT
    contract_type: ContractType = ContractType.GENERAL_CONTRACT
    review_stance: ReviewStance = ReviewStance.PARTY_A
    custom_rule_text: str = ""
    custom_rule_ids: list[str] = Field(default_factory=list)


class ReviewTaskCreateResponse(BaseModel):
    id: str
    status: ReviewTaskStatus
    created_at: datetime
    review_mode: ReviewMode
    contract_type: ContractType
    review_stance: ReviewStance


class UploadedFileResponse(BaseModel):
    id: str
    task_id: str
    filename: str
    content_type: str


class ReviewArtifactAvailability(BaseModel):
    report_ready: bool = False
    revised_contract_ready: bool = False
    diff_ready: bool = False


class ReviewTaskStatusResponse(BaseModel):
    id: str
    status: ReviewTaskStatus
    progress: int
    review_mode: ReviewMode
    contract_type: ContractType
    review_stance: ReviewStance
    custom_rules: CustomRuleInput = Field(default_factory=CustomRuleInput)
    summary: AggregatedReview | None = None
    workspace: ReviewWorkspace | None = None
    artifacts: ReviewArtifactAvailability = Field(default_factory=ReviewArtifactAvailability)


class ReviewAnalyzeResponse(BaseModel):
    id: str
    status: ReviewTaskStatus
    progress: int
    review_mode: ReviewMode


class ReviewIssuesResponse(BaseModel):
    task_id: str
    issues: list[ReviewIssue]


class ReviewReportResponse(BaseModel):
    report: ReportArtifact
    review: AggregatedReview
    report_content: ReviewReport


class RevisionDiffResponse(BaseModel):
    task_id: str
    review_mode: ReviewMode
    items: list[RevisionDiffItem]


class RevisedContractResponse(BaseModel):
    task_id: str
    review_mode: ReviewMode
    artifact: ReportArtifact
    diff_count: int
