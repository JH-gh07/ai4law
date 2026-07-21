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
    MANUAL_REVIEW = "MANUAL_REVIEW"


class DiagnosisSessionStatus(str, Enum):
    CREATED = "CREATED"
    ANSWERING = "ANSWERING"
    COMPLETED = "COMPLETED"


class TransferScenario(str, Enum):
    """出境场景类型（对应《促进和规范数据跨境流动规定》豁免情形）"""
    CONTRACT_PERFORMANCE = "contract_performance"   # 履行合同/向消费者提供服务
    HR_MANAGEMENT = "hr_management"                 # 跨国公司内部人力资源管理
    EMERGENCY = "emergency"                         # 紧急情况保护自然人生命健康财产
    LEGAL_DUTY = "legal_duty"                       # 履行法定职责或法定义务
    OTHER = "other"                                 # 其他商业目的


class ReceiverType(str, Enum):
    INTRA_GROUP = "intra_group"    # 集团内部关联公司
    THIRD_PARTY = "third_party"    # 独立第三方


class DiagnosisAnswerSet(BaseModel):
    is_ciio: TriState
    contains_important_data: TriState
    personal_info_count: int = Field(ge=0)
    sensitive_personal_info_count: int = Field(ge=0)
    transfer_purpose: str | None = None
    # V2 新增字段
    no_personal_info: TriState = TriState.NO
    transfer_scenario: TransferScenario = TransferScenario.OTHER
    receiver_type: ReceiverType = ReceiverType.THIRD_PARTY


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


class PIPIAHandoffResponse(ModuleHandoffBase):
    target_module: str = "pipia"
