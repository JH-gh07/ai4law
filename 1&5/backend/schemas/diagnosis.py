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
    EVALUATED = "EVALUATED"
    COMPLETED = "COMPLETED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PriorityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    HIGHEST = "HIGHEST"


class DiagnosisAnswerSet(BaseModel):
    is_ciio: TriState
    contains_important_data: TriState
    personal_info_count: int = Field(ge=0)
    sensitive_personal_info_count: int = Field(ge=0)
    transfer_purpose: str | None = None


class QuestionnaireItemDetail(BaseModel):
    selected: str | None = None
    selected_list: list[str] = Field(default_factory=list)
    text: str | None = None
    extra: dict = Field(default_factory=dict)


class ComplianceQuestionnaire(BaseModel):
    enterprise_name: str | None = None
    q1_2_industry: str
    q1_3_business_modes: list[str] = Field(default_factory=list)
    q1_4_service_targets: str
    q1_5_enterprise_size: str
    q1_6_is_ciio: TriState = TriState.UNCERTAIN

    q2_1_compliance_goals: list[str] = Field(default_factory=list)
    q2_2_has_incidents: str = "UNCLEAR"
    q2_2_incident_description: str | None = None
    q2_3_urgency: str
    q2_3_deadline: str | None = None

    q3_1_handles_personal_info: bool
    q3_2_personal_info_types: list[str] = Field(default_factory=list)
    q3_3_handles_important_data: bool = False
    q3_3_important_data_types: list[str] = Field(default_factory=list)
    q3_4_data_sources: list[str] = Field(default_factory=list)
    q3_5_processing_actions: list[str] = Field(default_factory=list)
    q3_6_data_volume: str
    q3_7_handles_enterprise_or_public_data: bool = False
    q3_7_data_detail: str | None = None
    q3_8_retention_policy: str
    q3_8_retention_detail: str | None = None

    q4_1_shares_with_third_parties: bool = False
    q4_1_third_party_detail: str | None = None
    q4_2_cross_border_transfer: bool = False
    q4_2_countries: list[str] = Field(default_factory=list)
    q4_2_exemption_scenarios: list[str] = Field(default_factory=list)
    q4_3_monetization: bool = False
    q4_3_monetization_detail: str | None = None
    q4_4_entrusted_processing: bool = False
    q4_4_entrusted_processing_detail: str | None = None
    q4_5_authorization_mechanism: str

    q5_1_systems: list[str] = Field(default_factory=list)
    q5_2_security_measures: list[str] = Field(default_factory=list)
    q5_3_compliance_documents: list[str] = Field(default_factory=list)
    q5_4_penalty_or_complaint_status: str
    q5_4_penalty_or_complaint_detail: str | None = None


class ComplianceProfileDraft(BaseModel):
    enterprise_name: str | None = None
    enterprise_attributes: dict = Field(default_factory=dict)
    business_overview: dict = Field(default_factory=dict)
    compliance_needs: dict = Field(default_factory=dict)
    data_profile: dict = Field(default_factory=dict)
    data_flow_profile: dict = Field(default_factory=dict)
    governance_profile: dict = Field(default_factory=dict)
    narrative_summary: str = ""


class DiagnosisCitation(BaseModel):
    source: str
    article: str
    note: str


class RuleHit(BaseModel):
    code: str
    question_refs: list[str]
    trigger_summary: str
    legal_basis: list[str]
    risk_level: RiskLevel
    priority: PriorityLevel


class RuleEvaluationResult(BaseModel):
    risk_level: RiskLevel
    outcome: DiagnosisOutcome
    hit_rules: list[RuleHit]
    legal_summary: list[str]
    compliance_conclusion: str
    path_conclusion: str
    priority_actions: list[str]
    citations: list[DiagnosisCitation]


class DiagnosisAssessmentReport(BaseModel):
    executive_summary: str
    profile_summary: str
    risk_analysis: str
    path_analysis: str
    next_actions: list[str]


class DiagnosisResult(BaseModel):
    outcome: DiagnosisOutcome
    risk_level: RiskLevel
    summary: str
    hit_rules: list[str]
    citations: list[DiagnosisCitation]
    next_actions: list[str]
    suggested_next_module: str | None = None
    profile_summary: str | None = None
    compliance_conclusion: str | None = None


class DiagnosisSessionCreateResponse(BaseModel):
    id: str
    status: DiagnosisSessionStatus


class DiagnosisSessionResponse(BaseModel):
    id: str
    status: DiagnosisSessionStatus
    questionnaire: ComplianceQuestionnaire | None = None
    profile: ComplianceProfileDraft | None = None
    evaluation: RuleEvaluationResult | None = None
    report_preview: DiagnosisAssessmentReport | None = None
    result: DiagnosisResult | None = None
    deprecated_answers: DiagnosisAnswerSet | None = None


class DiagnosisReportResponse(BaseModel):
    html_report: ReportArtifact
    pdf_report: ReportArtifact


class DiagnosisContextResponse(BaseModel):
    session_id: str
    outcome: DiagnosisOutcome | None = None
    risk_level: RiskLevel | None = None
    company_profile: dict = Field(default_factory=dict)
    prefill_context: dict = Field(default_factory=dict)


class ModuleHandoffBase(BaseModel):
    session_id: str
    source_module: str = "diagnosis"
    target_module: str
    recommended: bool
    diagnosis_outcome: DiagnosisOutcome
    risk_level: RiskLevel
    transfer_purpose: str | None = None
    questionnaire: ComplianceQuestionnaire
    profile: ComplianceProfileDraft
    evaluation: RuleEvaluationResult
    company_profile: dict = Field(default_factory=dict)
    prefill_form: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class AssessmentHandoffResponse(ModuleHandoffBase):
    target_module: str = "assessment"


class SCCHandoffResponse(ModuleHandoffBase):
    target_module: str = "scc"
