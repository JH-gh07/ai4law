"""CN SCC deterministic rule engine — hard thresholds and mandatory checks.

These rules handle clear YES/NO determinations that do not require LLM reasoning.
Agent outputs supplement but do not replace rule engine results.

Reference: doc/tmp/认证标准合同路径 Section 1 (Path Diagnosis), Section 2 (Data Classification)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.modules.scc.schema import (
    DataFieldItem,
    LegalBasis,
    PathDiagnosisInput,
    PathDiagnosisResult,
    PathType,
    RiskLevel,
)


# ── Threshold constants ──

SECURITY_ASSESSMENT_PII_THRESHOLD = 1_000_000
SECURITY_ASSESSMENT_SPI_THRESHOLD = 10_000
CIIO_TRIGGER = True  # CIIO always triggers security assessment
IMPORTANT_DATA_TRIGGER = True  # Important data always triggers security assessment


@dataclass
class RuleEngineResult:
    """Deterministic rule evaluation result."""

    # Path triggers
    triggers_security_assessment: bool = False
    triggers_security_assessment_reasons: list[str] = field(default_factory=list)

    # Threshold hits
    pii_threshold_hit: bool = False
    spi_threshold_hit: bool = False
    ciio_hit: bool = False
    important_data_hit: bool = False

    # Exemption indicators
    hr_exemption_possible: bool = False
    contract_necessity_possible: bool = False
    legal_obligation_possible: bool = False
    vital_interest_possible: bool = False

    # Path suitability
    standard_contract_suitable: bool = False
    certification_suitable: bool = False

    # Risk
    base_risk_level: RiskLevel = RiskLevel.LOW

    # Warnings
    warnings: list[str] = field(default_factory=list)


def evaluate_hard_thresholds(inp: PathDiagnosisInput) -> RuleEngineResult:
    """Evaluate deterministic thresholds and mandatory checks.

    Step 2 of Path Diagnosis: hard threshold judgment.
    """
    result = RuleEngineResult()

    # ── CIIO check ──
    if inp.is_ciio:
        result.ciio_hit = True
        result.triggers_security_assessment = True
        result.triggers_security_assessment_reasons.append(
            "企业为关键信息基础设施运营者(CIIO)，个人信息出境须通过安全评估"
        )

    # ── Important data check ──
    if inp.has_important_data:
        result.important_data_hit = True
        result.triggers_security_assessment = True
        result.triggers_security_assessment_reasons.append(
            "涉及重要数据出境，须通过安全评估"
        )

    # ── PII volume threshold ──
    if inp.pii_count >= SECURITY_ASSESSMENT_PII_THRESHOLD:
        result.pii_threshold_hit = True
        result.triggers_security_assessment = True
        result.triggers_security_assessment_reasons.append(
            f"个人信息出境规模({inp.pii_count:,}人)达到{ SECURITY_ASSESSMENT_PII_THRESHOLD:,}人门槛，触发安全评估"
        )

    # ── SPI volume threshold ──
    if inp.spi_count >= SECURITY_ASSESSMENT_SPI_THRESHOLD:
        result.spi_threshold_hit = True
        result.triggers_security_assessment = True
        result.triggers_security_assessment_reasons.append(
            f"敏感个人信息出境规模({inp.spi_count:,}人)达到{SECURITY_ASSESSMENT_SPI_THRESHOLD:,}人门槛，触发安全评估"
        )

    # ── Exemption assessment (Step 3) ──
    result.hr_exemption_posible = _check_hr_exemption(inp)
    result.contract_necessity_possible = _check_contract_necessity(inp)
    result.legal_obligation_possible = _check_legal_obligation(inp)
    result.vital_interest_possible = _check_vital_interest(inp)

    # ── Path suitability ──
    if not result.triggers_security_assessment:
        result.standard_contract_suitable = True
        if inp.is_certification_body or inp.has_certification_material:
            result.certification_suitable = True

    # ── Risk level ──
    result.base_risk_level = _compute_base_risk(inp, result)

    # ── Warnings ──
    _add_warnings(inp, result)

    return result


def _check_hr_exemption(inp: PathDiagnosisInput) -> bool:
    """Check if HR management exemption might apply."""
    return (
        inp.is_hr_management
        and inp.pii_count > 0
        and LegalBasis.hr_management in inp.legal_basis
    )


def _check_contract_necessity(inp: PathDiagnosisInput) -> bool:
    """Check if contract necessity exemption might apply."""
    return LegalBasis.contract_necessity in inp.legal_basis


def _check_legal_obligation(inp: PathDiagnosisInput) -> bool:
    """Check if legal obligation exemption might apply."""
    return LegalBasis.legal_obligation in inp.legal_basis


def _check_vital_interest(inp: PathDiagnosisInput) -> bool:
    """Check if vital interest exemption might apply."""
    return LegalBasis.vital_interest in inp.legal_basis


def _compute_base_risk(inp: PathDiagnosisInput, result: RuleEngineResult) -> RiskLevel:
    if result.triggers_security_assessment:
        return RiskLevel.HIGH
    if inp.spi_count > 0:
        return RiskLevel.MEDIUM
    if inp.pii_count >= 100_000:
        return RiskLevel.MEDIUM
    if inp.pii_count > 0:
        return RiskLevel.LOW
    return RiskLevel.LOW


def _add_warnings(inp: PathDiagnosisInput, result: RuleEngineResult) -> None:
    if result.hr_exemption_possible and not inp.has_exemption_material:
        result.warnings.append(
            "用户主张人力资源管理豁免，但未提供豁免材料（员工手册/集体合同），建议补充后再评估"
        )
    if inp.is_certification_body and not inp.has_certification_material:
        result.warnings.append(
            "用户选择认证路径，但需确认认证机构是否为中国网信部门认可的专业认证机构"
        )
    if inp.spi_count > 0 and inp.pii_count < 100:
        result.warnings.append(
            "敏感个人信息人数较少，但需关注具体字段类型和出境必要性"
        )


def determine_path(inp: PathDiagnosisInput, rule_result: RuleEngineResult) -> PathDiagnosisResult:
    """Determine the recommended path based on rule engine results.

    This is Step 5 of Path Diagnosis. Agent findings can override this.
    """
    blocking: list[str] = []
    next_questions: list[str] = []
    rationale_parts: list[str] = []

    # ── Determine primary path ──
    if rule_result.triggers_security_assessment:
        recommended: PathType = "security_assessment"
        rationale_parts.append(
            f"触发安全评估门槛：{'；'.join(rule_result.triggers_security_assessment_reasons)}"
        )
        alternative: PathType | None = None
        confidence = 0.90
    elif rule_result.hr_exemption_possible and inp.has_exemption_material:
        recommended = "exemption"
        rationale_parts.append("满足人力资源管理豁免条件，且已提供制度材料")
        alternative = "standard_contract"
        confidence = 0.70
        blocking.append("员工手册或集体合同中数据出境条款的完整性仍需核实")
        next_questions.append("是否能提供包含数据出境条款的最新版集体合同？")
    elif rule_result.hr_exemption_possible and not inp.has_exemption_material:
        recommended = "standard_contract"
        rationale_parts.append(
            "人力资源管理豁免可能适用，但证据不足；建议选择标准合同路径增强确定性"
        )
        alternative = "exemption"
        confidence = 0.60
        blocking.append("员工手册未明确数据出境条款")
        blocking.append("集体合同未专门提及数据出境")
        next_questions.append("是否已通过民主程序制定包含数据出境条款的劳动规章制度？")
        next_questions.append("是否能提供最新版集体合同？")
    elif inp.is_certification_body and inp.has_certification_material:
        recommended = "certification"
        rationale_parts.append("已提供认证材料，适用认证路径")
        alternative = "standard_contract"
        confidence = 0.75
        next_questions.append("认证机构是否在中国网信部门认可的专业认证机构名录内？")
    elif inp.is_certification_body and not inp.has_certification_material:
        recommended = "standard_contract"
        rationale_parts.append("用户选择认证路径但材料不足，标准合同路径替代")
        alternative = "certification"
        confidence = 0.55
        blocking.append("认证材料缺失，无法确认认证机构资质")
        next_questions.append("是否能提供认证机构的资质证明文件？")
    elif rule_result.standard_contract_suitable:
        recommended = "standard_contract"
        rationale_parts.append("未触发安全评估门槛，标准合同路径适用")
        alternative = None
        confidence = 0.85
    else:
        recommended = "uncertain"
        rationale_parts.append("当前信息不足以判定路径，需补充材料")
        alternative = None
        confidence = 0.30
        next_questions.append("请补充出境目的、接收方类型、数据处理规模等基本信息")

    # ── Add exemption assessment ──
    exemption_text = ""
    if rule_result.hr_exemption_possible:
        exemption_text += "人力资源管理豁免可能适用；"
    if rule_result.contract_necessity_possible:
        exemption_text += "合同所必需豁免可能适用；"
    if rule_result.legal_obligation_possible:
        exemption_text += "法定义务豁免可能适用；"
    if rule_result.vital_interest_possible:
        exemption_text += "紧急保护自然人生命健康财产豁免可能适用；"
    if not exemption_text:
        exemption_text = "当前信息未显示适用豁免场景"

    blocking.extend(rule_result.warnings)

    return PathDiagnosisResult(
        recommended_path=recommended,
        alternative_path=alternative,
        confidence=round(confidence, 2),
        rationale=" ".join(rationale_parts),
        blocking_issues=blocking,
        next_questions=next_questions[:5],
        triggered_thresholds=rule_result.triggers_security_assessment_reasons,
        exemption_assessment=exemption_text,
    )


# ── Field-level rules ──

# Known personal information field name patterns
PII_PATTERNS = {
    "name", "姓名", "full_name", "first_name", "last_name",
    "email", "邮箱", "email_address",
    "phone", "手机", "mobile", "phone_number", "telephone", "联系电话",
    "id_card", "身份证", "id_number", "passport", "护照",
    "address", "地址", "home_address", "work_address",
    "ip", "ip_address", "device_id", "mac", "mac_address",
    "bank_account", "银行卡", "account_number",
    "location", "gps", "经纬度", "position",
}

SPI_PATTERNS = {
    "health", "健康", "medical", "医疗", "disease", "疾病",
    "biometric", "生物识别", "fingerprint", "指纹", "face", "人脸",
    "religion", "宗教", "faith", "信仰",
    "political", "政治", "political_opinion",
    "sexual", "性取向", "sexual_orientation",
    "salary", "薪酬", "工资", "bonus", "奖金", "income", "收入",
    "finance", "金融", "credit", "征信", "bank_transaction", "交易记录",
    "race", "种族", "ethnicity", "ethnic_origin",
    "genetic", "基因", "dna",
    "criminal", "犯罪", "criminal_record",
    "minor", "未成年", "children", "儿童",
    "union", "工会", "trade_union",
}

# Fields that users commonly mislabel
COMMONLY_MISLABELED = {
    "Hashed_Device_ID": ("potential_personal_information", "哈希设备ID仍可能通过碰撞、关联分析或字典攻击实现重识别"),
    "Device_ID": ("personal_information", "设备标识符可唯一识别自然人，属于个人信息"),
    "IP_Address": ("personal_information", "IP地址可关联至特定设备或用户，属于个人信息"),
    "Cookie_ID": ("personal_information", "Cookie标识符可用于追踪用户行为，属于个人信息"),
    "Product_Category_Preference": ("potential_sensitive_personal_information", "包含母婴用品、医疗保健品等可能推断敏感状况的标签"),
    "Shopping_Preference": ("potential_sensitive_personal_information", "购物偏好可能推断个人的健康、性取向等敏感信息"),
    "Merchant_Contact_Name": ("personal_information", "商户联系人姓名可识别自然人，属于个人信息"),
    "Merchant_Contact_Email": ("personal_information", "商户联系邮箱可识别自然人，属于个人信息"),
}


def check_field_mislabel(field: DataFieldItem) -> tuple[str, str, RiskLevel]:
    """Check a single field for obvious mislabeling. Returns (judgment, reason, risk)."""
    name_lower = field.field_name.lower()

    # Check known mislabel patterns
    for key, (judgment, reason) in COMMONLY_MISLABELED.items():
        if key.lower() in name_lower:
            return judgment, reason, RiskLevel.MEDIUM

    # Check SPI patterns against user label
    for spi_word in SPI_PATTERNS:
        if spi_word.lower() in name_lower or spi_word.lower() in field.field_description.lower():
            if "not_personal" in field.user_pii_label.lower():
                return ("potential_sensitive_personal_information",
                        f"字段名称/描述含'{spi_word}'，可能属于敏感个人信息，用户标注为非个人信息需重新评估",
                        RiskLevel.HIGH)
            if "personal" in field.user_pii_label.lower() and "sensitive" not in field.user_spi_label.lower():
                return ("potential_sensitive_personal_information",
                        f"字段名称/描述含'{spi_word}'，可能属于敏感个人信息，用户未标注为敏感信息",
                        RiskLevel.HIGH)

    # Check PII patterns against user label
    match_found = False
    for pii_word in PII_PATTERNS:
        if pii_word.lower() in name_lower or pii_word.lower() in field.field_description.lower():
            match_found = True
            break

    if match_found and "not_personal" in field.user_pii_label.lower():
        return ("potential_personal_information",
                "字段名称与已知个人信息类型匹配，用户标注为非个人信息可能不准确",
                RiskLevel.MEDIUM)

    # Check anonymization claims
    if field.processing_method.value in ("hashed", "masked") and "anonymized" in field.user_pii_label.lower():
        return ("potential_personal_information",
                "用户声称已匿名化，但处理方式为哈希/脱敏而非匿名化，仍存在重标识化风险",
                RiskLevel.MEDIUM)

    return ("", "", RiskLevel.LOW)
