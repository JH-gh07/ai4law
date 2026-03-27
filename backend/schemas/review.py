from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from backend.schemas.common import ReportArtifact


class ReviewTaskStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADED = "UPLOADED"
    SEGMENTING = "SEGMENTING"
    CLASSIFYING = "CLASSIFYING"
    REVIEWING = "REVIEWING"
    AGGREGATING = "AGGREGATING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ClauseType(str, Enum):
    DATA_PROCESSING_SCOPE = "DATA_PROCESSING_SCOPE"
    CONSENT_NOTICE = "CONSENT_NOTICE"
    SECURITY_MEASURES = "SECURITY_MEASURES"
    CROSS_BORDER_TRANSFER = "CROSS_BORDER_TRANSFER"
    RIGHTS_REQUEST = "RIGHTS_REQUEST"
    LIABILITY = "LIABILITY"
    OTHER = "OTHER"


class ReviewSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


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


class ClassifiedClause(Clause):
    clause_type: ClauseType
    matched_keywords: list[str] = Field(default_factory=list)


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
    position: ClausePosition = Field(default_factory=ClausePosition)


class AggregatedReview(BaseModel):
    overall_rating: str
    summary: str
    issues: list[ReviewIssue]
    issue_counts: dict[str, int]
    priority_actions: list[str]


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


class ReviewIssuesResponse(BaseModel):
    task_id: str
    issues: list[ReviewIssue]


class ReviewReportResponse(BaseModel):
    report: ReportArtifact
    review: AggregatedReview
