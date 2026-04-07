from enum import Enum

from pydantic import BaseModel, Field

from backend.schemas.common import ReportArtifact


class TriState(str, Enum):
    YES = "YES"
    NO = "NO"
    UNCERTAIN = "UNCERTAIN"


class DiagnosisOutcome(str, Enum):
    SECURITY_ASSESSMENT = "SECURITY_ASSESSMENT"
    SCC_OR_CERTIFICATION = "SCC_OR_CERTIFICATION"
    EXEMPTION = "EXEMPTION"


class DiagnosisSessionStatus(str, Enum):
    CREATED = "CREATED"
    ANSWERING = "ANSWERING"
    COMPLETED = "COMPLETED"


class DiagnosisAnswerSet(BaseModel):
    is_ciio: TriState
    contains_important_data: TriState
    personal_info_count: int = Field(ge=0)
    sensitive_personal_info_count: int = Field(ge=0)
    transfer_purpose: str | None = None


class DiagnosisCitation(BaseModel):
    source: str
    article: str
    note: str


class DiagnosisResult(BaseModel):
    outcome: DiagnosisOutcome
    summary: str
    hit_rules: list[str]
    citations: list[DiagnosisCitation]
    next_actions: list[str]
    suggested_next_module: str | None = None


class DiagnosisSessionCreateResponse(BaseModel):
    id: str
    status: DiagnosisSessionStatus


class DiagnosisSessionResponse(BaseModel):
    id: str
    status: DiagnosisSessionStatus
    answers: DiagnosisAnswerSet | None = None
    result: DiagnosisResult | None = None


class DiagnosisReportResponse(BaseModel):
    html_report: ReportArtifact
    pdf_report: ReportArtifact


class DiagnosisContextResponse(BaseModel):
    session_id: str
    outcome: DiagnosisOutcome | None = None
    company_profile: dict = Field(default_factory=dict)
    prefill_context: dict = Field(default_factory=dict)


class ModuleHandoffBase(BaseModel):
    session_id: str
    source_module: str = "diagnosis"
    target_module: str
    recommended: bool
    diagnosis_outcome: DiagnosisOutcome
    transfer_purpose: str | None = None
    company_profile: dict = Field(default_factory=dict)
    prefill_form: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class AssessmentHandoffResponse(ModuleHandoffBase):
    target_module: str = "assessment"


class SCCHandoffResponse(ModuleHandoffBase):
    target_module: str = "scc"
