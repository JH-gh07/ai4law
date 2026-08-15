from enum import Enum

from pydantic import BaseModel, Field

from backend.common.legal_control.contracts import LegalControlDecision


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

    # ── 问卷扩展：业务基础信息（模块1）──────────────────────────────
    m1_enterprise_name: str = ""
    m1_industry: str = ""
    m1_business_channels: list[str] = Field(default_factory=list)
    m1_service_targets: str = ""
    m1_company_size: str = ""

    # ── 问卷扩展：合规需求与现状（模块2）───────────────────────────
    m2_core_needs: list[str] = Field(default_factory=list)
    m2_had_compliance_issue: str = ""
    m2_issue_description: str = ""
    m2_deadline: str = ""

    # ── 问卷扩展：数据处理核心信息（模块3）─────────────────────────
    m3_processes_personal_info: str = ""
    m3_personal_info_types: list[str] = Field(default_factory=list)
    m3_sensitive_info_types: list[str] = Field(default_factory=list)
    m3_processes_important_data: str = ""
    m3_important_data_types: list[str] = Field(default_factory=list)
    m3_data_sources: list[str] = Field(default_factory=list)
    m3_processing_activities: list[str] = Field(default_factory=list)
    m3_data_volume_range: str = ""
    m3_processes_enterprise_public_data: str = ""
    m3_enterprise_public_data_desc: str = ""
    m3_retention_period: str = ""
    m3_retention_desc: str = ""

    # ── 问卷扩展：数据流转与共享情况（模块4）───────────────────────
    m4_share_to_third_party: str = ""
    m4_third_party_types: str = ""
    m4_cross_border_transfer: str = ""
    m4_cross_border_regions: str = ""
    m4_commercialization: str = ""
    m4_commercialization_mode: str = ""
    m4_entrusted_processing: str = ""
    m4_entrusted_party_type: str = ""
    m4_authorization_method: str = ""

    # ── 问卷扩展：业务系统与技术架构（模块5）───────────────────────
    m5_systems: list[str] = Field(default_factory=list)
    m5_security_measures: list[str] = Field(default_factory=list)
    m5_compliance_docs: list[str] = Field(default_factory=list)
    m5_penalty_or_complaint: str = ""
    m5_penalty_time: str = ""
    m5_penalty_reason: str = ""
    m5_penalty_result: str = ""


class DiagnosisResult(BaseModel):
    recommended_path: str
    legal_basis: list[str]
    rationale: str
    action_items: list[str]
    risk_level: str
    conclusion_source: str = Field(default="rule")
    confidence: str = Field(default="HIGH")
    matched_rule_id: str | None = None
    final_explanation: str = ""
    uncertainty_notes: list[str] = Field(default_factory=list)
    fact_provenance: dict[str, str] = Field(default_factory=dict)
    missing_facts: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    # ── Legal Agent Control Plane（task073，additive，opt-in） ──
    control_decision: LegalControlDecision | None = None
    clarification_questions: list[str] = Field(default_factory=list)


class DiagnosisReportRequest(BaseModel):
    company_name: str = Field(min_length=2)
    answers: DiagnosisAnswers


class DiagnosisReportResponse(BaseModel):
    report_path: str
    html_report_path: str
    pdf_report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    result: DiagnosisResult
