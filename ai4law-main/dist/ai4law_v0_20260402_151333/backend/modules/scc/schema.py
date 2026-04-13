from pydantic import BaseModel, Field


class SCCRequest(BaseModel):
    company_name: str = Field(min_length=2)
    receiver_name: str = Field(min_length=2)
    receiver_country: str = Field(min_length=2)
    transfer_purpose: str = Field(min_length=2)
    pii_count: int = Field(default=0, ge=0)
    spi_count: int = Field(default=0, ge=0)
    has_scc_draft: bool = False
    uploaded_files: list[str] = Field(default_factory=list)


class SCCProfile(BaseModel):
    company_name: str
    receiver_name: str
    receiver_country: str
    transfer_purpose: str
    pii_count: int
    spi_count: int
    has_scc_draft: bool
    extracted_notes: list[str] = Field(default_factory=list)


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
