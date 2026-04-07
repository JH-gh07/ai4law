from pydantic import BaseModel, Field

from backend.modules.assessment.task_state import AssessmentTaskState


class AssessmentRequest(BaseModel):
    company_name: str = Field(min_length=2)
    industry: str = Field(default="")
    is_ciio: bool = False
    contains_important_data: bool = False
    pii_count: int = Field(default=0, ge=0)
    spi_count: int = Field(default=0, ge=0)
    transfer_purpose: str = Field(min_length=2)
    receiver_country: str = Field(min_length=2)
    uploaded_files: list[str] = Field(default_factory=list)


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
