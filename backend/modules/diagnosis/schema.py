from enum import Enum

from pydantic import BaseModel, Field


class YesNoUnknown(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class TransferScenario(str, Enum):
    """出境场景类型（对应《促进和规范数据跨境流动规定》豁免情形）"""
    CONTRACT_PERFORMANCE = "contract_performance"   # 履行合同/向消费者提供服务
    HR_MANAGEMENT = "hr_management"                 # 跨国公司内部人力资源管理
    EMERGENCY = "emergency"                         # 紧急情况保护自然人生命健康财产
    LEGAL_DUTY = "legal_duty"                       # 履行法定职责或法定义务
    OTHER = "other"                                 # 其他商业目的


class ReceiverType(str, Enum):
    """境外接收方类型"""
    INTRA_GROUP = "intra_group"    # 集团内部关联公司
    THIRD_PARTY = "third_party"    # 独立第三方


class DiagnosisAnswers(BaseModel):
    # ── 原有4题（核心阈值判断）──────────────────────────────────────
    q1_is_ciio: YesNoUnknown = Field(description="是否为关键信息基础设施运营者(CIIO)")
    q2_has_important_data: YesNoUnknown = Field(description="是否向境外提供重要数据")
    q3_pii_count: int = Field(ge=0, description="近12个月累计向境外提供个人信息的人数")
    q4_spi_count: int = Field(ge=0, description="近12个月累计向境外提供敏感个人信息的人数")

    # ── V2 新增题（豁免情形与场景判断）──────────────────────────────
    q5_no_personal_info: YesNoUnknown = Field(
        default=YesNoUnknown.NO,
        description="出境数据是否不含个人信息且不涉及重要数据（纯业务/技术数据）",
    )
    q6_scenario: TransferScenario = Field(
        default=TransferScenario.OTHER,
        description="本次数据出境的主要业务场景",
    )
    q7_receiver_type: ReceiverType = Field(
        default=ReceiverType.THIRD_PARTY,
        description="境外数据接收方类型",
    )
    q8_purpose: str = Field(
        default="",
        description="出境目的简述（供LLM生成专业说明使用）",
    )


class DiagnosisResult(BaseModel):
    recommended_path: str
    legal_basis: list[str]
    rationale: str
    action_items: list[str]
    risk_level: str


class DiagnosisReportRequest(BaseModel):
    company_name: str = Field(min_length=2)
    answers: DiagnosisAnswers


class DiagnosisReportResponse(BaseModel):
    report_path: str
    html_report_path: str
    pdf_report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    result: DiagnosisResult
