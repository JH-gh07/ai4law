"""EO 14117 deterministic rule engine — 8-stage analysis pipeline.

All logic is pure Python (no LLM). Produces a RuleEngineResult that
drives all downstream pipeline stages (facts, issues, evidence, chapters).

Stage 1 — Data type classification (DOJ categories)
Stage 2 — Bulk threshold check
Stage 3 — Covered person / country of concern inference
Stage 4 — Transaction type classification
Stage 5 — Prohibited transaction check
Stage 6 — Restricted transaction check
Stage 7 — Security measures gap analysis
Stage 8 — Traffic light resolution
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.domains.us.eo14117.schema import (
    US14117AccessPerson,
    US14117DataItem,
    US14117Entity,
    US14117Request,
    US14117RiskMatrixRow,
    US14117RuleEngineResult,
    US14117RuleHit,
    US14117SecurityMeasure,
    US14117TrafficLightResult,
)

# ═════════════════════════════════════════════════════════════════════════
# Configuration constants
# ═════════════════════════════════════════════════════════════════════════

# EO 14117 §100.1 — Countries of concern with aliases
# Each standard key maps to a list of aliases (lowercase, both EN and CN)
_COUNTRY_OF_CONCERN_ALIASES: dict[str, list[str]] = {
    "china": [
        "china", "people's republic of china", "prc", "中国",
        "中华人民共和国", "mainland china", "中国内地",
    ],
    "russia": [
        "russia", "russian federation", "俄罗斯",
        "俄罗斯联邦",
    ],
    "north_korea": [
        "north korea", "dprk", "democratic people's republic of korea",
        "朝鲜", "朝鲜民主主义人民共和国",
    ],
    "iran": [
        "iran", "islamic republic of iran", "伊朗",
        "伊朗伊斯兰共和国",
    ],
    "cuba": [
        "cuba", "古巴",
    ],
    "venezuela": [
        "venezuela", "bolivarian republic of venezuela", "委内瑞拉",
        "委内瑞拉玻利瓦尔共和国",
    ],
}

# Standard English -> Chinese display names
_COUNTRY_OF_CONCERN_NAMES: dict[str, str] = {
    "china": "中国",
    "russia": "俄罗斯",
    "north_korea": "朝鲜",
    "iran": "伊朗",
    "cuba": "古巴",
    "venezuela": "委内瑞拉",
}

# Special jurisdictions — flagged but merits legal review before categorization
_SPECIAL_JURISDICTIONS: dict[str, str] = {
    "hong kong": "china",
    "hong kong sar": "china",
    "香港": "china",
    "macau": "china",
    "macao": "china",
    "澳门": "china",
    "taiwan": "needs_review",
    "台湾": "needs_review",
    "chinese taipei": "needs_review",
}


def _match_country_of_concern(text: str) -> tuple[bool, str, str]:
    """Check if text matches any country of concern.

    Returns (is_match, standard_country_key, matched_text).
    For special jurisdictions (HK/Macau), returns (True, "needs_review", reason).
    """
    normalized = _normalize(text)
    if not normalized:
        return False, "", ""

    # Check special jurisdictions first
    for special_name, disposition in _SPECIAL_JURISDICTIONS.items():
        if special_name in normalized:
            return True, "needs_review", f"Special jurisdiction '{text}' requires legal review (assoc: {disposition})"

    # Check country of concern aliases
    for std_key, aliases in _COUNTRY_OF_CONCERN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                return True, std_key, alias

    return False, "", ""

# EO 14117 §100.2 / §100.3 — Bulk thresholds per DOJ data category
BULK_THRESHOLDS: dict[str, int] = {
    "human_genomic_data": 100,
    "biometric_identifiers": 1000,
    "precise_geolocation_data": 1000,
    "personal_health_data": 10000,
    "personal_financial_data": 10000,
    "covered_personal_identifiers": 100000,
    "government_related_data": 1,  # any amount triggers
    "not_14117_data": 999_999_999,  # effectively never triggers
}

# EO 14117 — Required security measures for restricted transactions (§100.3)
REQUIRED_SECURITY_MEASURES = {
    "access_control": [
        "logical_isolation_of_covered_data",
        "multi_factor_authentication",
        "least_privilege_access",
        "role_based_access_control",
    ],
    "encryption": [
        "encryption_at_rest",
        "encryption_in_transit",
        "key_management",
    ],
    "data_minimization": [
        "data_aggregation",
        "de_identification_or_pseudonymization",
        "purpose_limitation_controls",
    ],
    "audit_logging": [
        "comprehensive_activity_logs",
        "log_retention_minimum_1_year",
        "real_time_alerting",
        "independent_audit_quarterly",
    ],
    "personnel_controls": [
        "employee_training_program",
        "confidentiality_agreements",
        "background_checks",
    ],
    "contractual_controls": [
        "onward_transfer_restrictions",
        "data_deletion_on_termination",
        "audit_rights_clause",
        "breach_notification_clause",
    ],
}

# Security measure aliases for fuzzy matching — standard ID → alternative phrasings
_SECURITY_MEASURE_ALIASES: dict[str, list[str]] = {
    "logical_isolation_of_covered_data": [
        "isolated workspace", "隔离工作区", "logical isolation",
        "sandbox environment", "sandbox", "隔离环境",
        "segmented network", "network segmentation", "网络隔离",
        "secure enclave", "dedicated environment",
    ],
    "multi_factor_authentication": [
        "mfa", "multi-factor", "2fa", "two factor", "two-factor",
        "多因素认证", "双重认证", "双因素", "二次验证",
        "强身份认证", "strong authentication",
    ],
    "least_privilege_access": [
        "least privilege", "minimum privilege", "最小权限",
        "minimum access", "need to know", "least access",
        "poLP", "principle of least privilege",
    ],
    "role_based_access_control": [
        "rbac", "role based access", "role-based access",
        "基于角色的访问控制", "角色权限",
    ],
    "encryption_at_rest": [
        "静置加密", "静态加密", "at rest encryption",
        "aes-256", "aes256", "disk encryption", "storage encryption",
        "数据库加密", "database encryption",
    ],
    "encryption_in_transit": [
        "传输加密", "in transit encryption", "tls", "ssl",
        "https", "tls 1.3", "transport encryption",
    ],
    "key_management": [
        "密钥管理", "key rotation", "hsm", "hardware security module",
        "kms", "key vault",
    ],
    "data_aggregation": [
        "数据聚合", "aggregation", "聚合统计", "k-anonymity",
        "differential privacy", "差分隐私",
    ],
    "de_identification_or_pseudonymization": [
        "去标识化", "假名化", "de-identification", "pseudonymization",
        "tokenization", "匿名化", "anonymization",
        "data masking", "数据脱敏",
    ],
    "purpose_limitation_controls": [
        "目的限制", "purpose limitation", "use limitation",
        "purpose binding", "数据用途限制",
    ],
    "comprehensive_activity_logs": [
        "全量日志", "完整日志", "活动日志", "activity logs",
        "access logs", "审计日志", "audit logs", "audit trail",
        "全面活动日志",
    ],
    "log_retention_minimum_1_year": [
        "日志保存", "log retention", "保留1年", "保存1年",
        "至少1年", "minimum 1 year", "retention period",
    ],
    "real_time_alerting": [
        "实时告警", "实时预警", "real time alert", "alerting",
        "siem", "security monitoring", "安全监控",
    ],
    "independent_audit_quarterly": [
        "独立审计", "季度审计", "independent audit", "quarterly audit",
        "third party audit", "第三方审计", "external audit",
        "定期审计", "periodic audit",
    ],
    "employee_training_program": [
        "员工培训", "employee training", "security awareness",
        "安全意识培训", "training program", "security training",
    ],
    "confidentiality_agreements": [
        "保密协议", "confidentiality agreement", "nda",
        "non-disclosure agreement", "secrecy agreement",
    ],
    "background_checks": [
        "背景调查", "background check", "personnel screening",
        "员工背景审查", "security clearance",
    ],
    "onward_transfer_restrictions": [
        "禁止再传输", "再传输限制", "onward transfer restriction",
        "no subprocessing", "禁止转委托", "sub-processing restriction",
        "禁止再转让", "no onward sharing",
    ],
    "data_deletion_on_termination": [
        "终止删除", "合同终止删除", "deletion on termination",
        "data destruction", "数据销毁", "return or destroy",
    ],
    "audit_rights_clause": [
        "审计权", "audit rights", "inspection right",
        "right to audit", "审计条款",
    ],
    "breach_notification_clause": [
        "违约通知", "breach notification", "incident notification",
        "security incident reporting", "安全事件通知",
    ],
}

# Keywords for data category auto-classification
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "human_genomic_data": [
        "genomic", "genome", "dna", "rna", "genetic sequence",
        "whole genome", "全基因组", "基因测序", "基因组",
        "human genomic", "germline",
    ],
    "biometric_identifiers": [
        "biometric", "fingerprint", "facial recognition", "face scan",
        "iris scan", "retina", "voice print", "voiceprint",
        "生物识别", "指纹", "面部识别", "虹膜", "声纹",
    ],
    "precise_geolocation_data": [
        "precise geolocation", "gps coordinate", "gps轨迹",
        "gps tracking", "real-time location", "latitude longitude",
        "精确地理位置", "精确定位", "gps定位",
    ],
    "personal_health_data": [
        "health", "medical", "patient", "diagnosis", "prescription",
        "clinical", "disease", "treatment", "pharmaceutical",
        "健康", "医疗", "病历", "诊断", "处方",
    ],
    "personal_financial_data": [
        "financial", "bank", "credit", "income", "transaction",
        "asset", "liability", "loan", "mortgage", "investment portfolio",
        "金融", "银行", "信用", "收入", "资产",
    ],
    "covered_personal_identifiers": [
        "email", "phone", "address", "identifier", "social security",
        "government id", "driver license", "passport number",
        "邮箱", "电话", "地址", "身份证", "护照",
    ],
    "government_related_data": [
        "government", "federal", "military", "defense", "intelligence",
        "law enforcement", "classified", "sensitive but unclassified",
        "政府", "联邦", "军事", "国防", "情报", "执法",
    ],
}

# Non-precise location disambiguators
_NON_PRECISE_LOCATION_KEYWORDS = [
    "city level", "city-level", "市级", "城市级", "metropolitan area",
    "zip code", "postal code", "邮编", "邮政编码",
    "ip geolocation", "coarse location",
]


# ═════════════════════════════════════════════════════════════════════════
# Dataclasses for intermediate results
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class DataClassification:
    data_item_name: str
    doj_category: str
    bulk_threshold: int
    threshold_hit: bool
    us_person_count: int
    is_government_related: bool
    confidence: float = 0.8
    reasoning: str = ""


@dataclass
class EntityAssessment:
    entity_name: str
    is_country_of_concern: bool = False
    country_of_concern_reason: str = ""
    is_covered_person: bool = False
    covered_person_status: str = "not_covered"  # confirmed | inferred | needs_review | not_covered
    covered_person_reasons: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)  # due diligence gaps
    confidence: float = 0.8


@dataclass
class TransactionAssessment:
    transaction_type: str = "other"
    is_data_brokerage: bool = False
    involves_covered_person: bool = False
    involves_bulk_sensitive: bool = False
    involves_government_data: bool = False
    is_prohibited: bool = False
    is_restricted: bool = False
    prohibition_reasons: list[str] = field(default_factory=list)
    restriction_reasons: list[str] = field(default_factory=list)


@dataclass
class SecurityGapReport:
    required_measures: list[str] = field(default_factory=list)
    implemented: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    partial_measures: list[str] = field(default_factory=list)  # alias-matched but not exact
    is_compliant: bool = False


# ═════════════════════════════════════════════════════════════════════════
# Stage 1 — Data type classification
# ═════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    return text.strip().lower()


def _matches_any_keyword(text: str, keywords: list[str]) -> bool:
    lowered = _normalize(text)
    return any(kw.lower() in lowered for kw in keywords)


def classify_single_data_item(item: US14117DataItem) -> DataClassification:
    """Classify one data item into a DOJ category using keyword + field matching."""
    # Build a searchable text blob
    search_text = " ".join([
        item.data_item_name,
        item.data_description,
        item.business_context,
        item.data_subject_type,
        item.doj_data_category,
        item.precision_level,
    ])

    # If user explicitly set doj_data_category, respect it
    if item.doj_data_category and item.doj_data_category != "not_14117_data":
        category = item.doj_data_category
        threshold = BULK_THRESHOLDS.get(category, 999_999_999)
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category=category,
            bulk_threshold=threshold,
            threshold_hit=item.us_person_count >= threshold,
            us_person_count=item.us_person_count,
            is_government_related=item.is_government_related or category == "government_related_data",
            confidence=0.9,
            reasoning=f"User-specified category: {category}",
        )

    # Auto-classify by keyword matching (check most specific categories first)
    # 1. Government-related check
    if item.is_government_related or _matches_any_keyword(search_text, _CATEGORY_KEYWORDS["government_related_data"]):
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category="government_related_data",
            bulk_threshold=1,
            threshold_hit=item.us_person_count >= 1,
            us_person_count=item.us_person_count,
            is_government_related=True,
            confidence=0.85,
            reasoning="Matched government-related data keywords or field flag.",
        )

    # 2. Human genomic data
    if _matches_any_keyword(search_text, _CATEGORY_KEYWORDS["human_genomic_data"]):
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category="human_genomic_data",
            bulk_threshold=100,
            threshold_hit=item.us_person_count >= 100,
            us_person_count=item.us_person_count,
            is_government_related=False,
            confidence=0.85,
            reasoning="Matched human genomic / DNA / genetic sequence keywords.",
        )

    # 3. Precise geolocation — with anti-false-positive check
    if _matches_any_keyword(search_text, _CATEGORY_KEYWORDS["precise_geolocation_data"]):
        if _matches_any_keyword(search_text, _NON_PRECISE_LOCATION_KEYWORDS):
            # city-level / zip-code level → not precise geolocation
            pass  # fall through to other checks
        else:
            return DataClassification(
                data_item_name=item.data_item_name,
                doj_category="precise_geolocation_data",
                bulk_threshold=1000,
                threshold_hit=item.us_person_count >= 1000,
                us_person_count=item.us_person_count,
                is_government_related=False,
                confidence=0.85,
                reasoning="Matched precise geolocation keywords; non-precise disambiguators not found.",
            )

    # 4. Biometric identifiers
    if _matches_any_keyword(search_text, _CATEGORY_KEYWORDS["biometric_identifiers"]):
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category="biometric_identifiers",
            bulk_threshold=1000,
            threshold_hit=item.us_person_count >= 1000,
            us_person_count=item.us_person_count,
            is_government_related=False,
            confidence=0.85,
            reasoning="Matched biometric / fingerprint / facial recognition keywords.",
        )

    # 5. Personal health data
    if _matches_any_keyword(search_text, _CATEGORY_KEYWORDS["personal_health_data"]):
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category="personal_health_data",
            bulk_threshold=10000,
            threshold_hit=item.us_person_count >= 10000,
            us_person_count=item.us_person_count,
            is_government_related=False,
            confidence=0.80,
            reasoning="Matched health / medical / clinical keywords.",
        )

    # 6. Personal financial data
    if _matches_any_keyword(search_text, _CATEGORY_KEYWORDS["personal_financial_data"]):
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category="personal_financial_data",
            bulk_threshold=10000,
            threshold_hit=item.us_person_count >= 10000,
            us_person_count=item.us_person_count,
            is_government_related=False,
            confidence=0.80,
            reasoning="Matched financial / bank / credit keywords.",
        )

    # 7. Check sensitive flags — when data is sensitive but category is unclear
    if item.is_sensitive_personal_info:
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category="covered_personal_identifiers",
            bulk_threshold=100000,
            threshold_hit=item.us_person_count >= 100000,
            us_person_count=item.us_person_count,
            is_government_related=False,
            confidence=0.60,
            reasoning="Marked sensitive but category unclear; defaulted to covered personal identifiers.",
        )

    # 8. Covered personal identifiers (broadest catch)
    if _matches_any_keyword(search_text, _CATEGORY_KEYWORDS["covered_personal_identifiers"]):
        return DataClassification(
            data_item_name=item.data_item_name,
            doj_category="covered_personal_identifiers",
            bulk_threshold=100000,
            threshold_hit=item.us_person_count >= 100000,
            us_person_count=item.us_person_count,
            is_government_related=False,
            confidence=0.75,
            reasoning="Matched personal identifier keywords (email, phone, etc.).",
        )

    # 9. Not 14117 data
    return DataClassification(
        data_item_name=item.data_item_name,
        doj_category="not_14117_data",
        bulk_threshold=999_999_999,
        threshold_hit=False,
        us_person_count=item.us_person_count,
        is_government_related=False,
        confidence=0.70,
        reasoning="No matching DOJ category found; classified as non-14117 data.",
    )


def classify_data_items(items: list[US14117DataItem]) -> list[DataClassification]:
    """Stage 1: Classify all data items into DOJ categories."""
    return [classify_single_data_item(item) for item in items]


# ═════════════════════════════════════════════════════════════════════════
# Stage 2 — Bulk threshold check
# ═════════════════════════════════════════════════════════════════════════

def check_bulk_thresholds(
    classifications: list[DataClassification],
    overrides: dict[str, int] | None = None,
) -> list[DataClassification]:
    """Stage 2: Update threshold_hit field for each classification.

    Args:
        classifications: Data classifications from Stage 1.
        overrides: Optional per-category threshold overrides (from US14117Request).
    """
    for c in classifications:
        threshold = c.bulk_threshold
        if overrides and c.doj_category in overrides:
            threshold = overrides[c.doj_category]
        c.threshold_hit = c.us_person_count >= threshold
        c.bulk_threshold = threshold  # update with override value
    return classifications


# ═════════════════════════════════════════════════════════════════════════
# Stage 3 — Covered person / country of concern inference
# ═════════════════════════════════════════════════════════════════════════


def infer_covered_person_for_entity(
    entity: US14117Entity,
    access_persons: list[US14117AccessPerson],
) -> EntityAssessment:
    """Stage 3: Infer covered person status with tri-state classification.

    Returns:
        EntityAssessment with covered_person_status set to one of:
        - "confirmed": strong evidence (government control, COC registration + non-special)
        - "inferred": moderate evidence (governing law, investment, ownership text, access persons)
        - "needs_review": special jurisdiction (HK/Macau/Taiwan) or insufficient information
        - "not_covered": no triggers detected
    """
    assessment = EntityAssessment(entity_name=entity.entity_name)

    # If user already marked it, trust the user but note the source
    if entity.is_covered_person is True:
        assessment.is_covered_person = True
        assessment.covered_person_status = "confirmed"
        assessment.covered_person_reasons.append("User-confirmed as covered person.")
        assessment.confidence = 1.0
        return assessment

    user_said_not_covered = entity.is_covered_person is False

    # Accumulate signals
    has_strong_signal = False
    has_moderate_signal = False
    special_jurisdiction_hit = False
    special_jurisdiction_detail = ""

    # Check 1: Country of registration
    is_match, std_key, matched = _match_country_of_concern(entity.country_of_registration)
    if is_match:
        if std_key == "needs_review":
            special_jurisdiction_hit = True
            special_jurisdiction_detail = matched
            assessment.missing_information.append(
                f"Entity '{entity.entity_name}' is registered in {entity.country_of_registration}. "
                f"Please clarify: (1) whether it is controlled by a country-of-concern entity; "
                f"(2) the applicable governing law; (3) the ultimate beneficial owner."
            )
        else:
            assessment.is_country_of_concern = True
            coc_label = _COUNTRY_OF_CONCERN_NAMES.get(std_key, std_key)
            assessment.country_of_concern_reason = (
                f"Registered in country of concern: {entity.country_of_registration} ({coc_label})"
            )
            assessment.covered_person_reasons.append(assessment.country_of_concern_reason)
            has_strong_signal = True
            assessment.confidence = 0.90

    # Check 2: Governing law
    if entity.governing_law:
        is_match_law, std_key_law, matched_law = _match_country_of_concern(entity.governing_law)
        if is_match_law and std_key_law != "needs_review":
            coc_label = _COUNTRY_OF_CONCERN_NAMES.get(std_key_law, std_key_law)
            assessment.covered_person_reasons.append(
                f"Governed by law of country of concern: {entity.governing_law} ({coc_label})"
            )
            has_moderate_signal = True
            assessment.confidence = max(assessment.confidence, 0.80)
        elif is_match_law and std_key_law == "needs_review":
            assessment.missing_information.append(
                f"Governing law '{entity.governing_law}' may be associated with a country of concern. "
                f"Please clarify the applicable legal framework and whether it confers control."
            )

    # Check 3: Government control — strong signal
    if entity.government_control:
        assessment.covered_person_reasons.append(
            "Entity is under government control of a country of concern."
        )
        has_strong_signal = True
        assessment.confidence = max(assessment.confidence, 0.85)

    # Check 4: Government investment — moderate signal (investment ≠ control)
    if entity.government_investment:
        inv_lower = entity.government_investment.lower()
        for std_key, aliases in _COUNTRY_OF_CONCERN_ALIASES.items():
            for alias in aliases:
                if alias in inv_lower:
                    coc_label = _COUNTRY_OF_CONCERN_NAMES.get(std_key, std_key)
                    reason = f"Receives government investment from {coc_label}: {entity.government_investment[:120]}"
                    if reason not in assessment.covered_person_reasons:
                        assessment.covered_person_reasons.append(reason)
                    has_moderate_signal = True
                    assessment.confidence = max(assessment.confidence, 0.75)
                    # Ask for clarification
                    assessment.missing_information.append(
                        f"Entity '{entity.entity_name}' has government investment ({coc_label}). "
                        f"Please clarify: (1) investment percentage; (2) board seats or veto rights; "
                        f"(3) whether the investor exercises control over data processing."
                    )
                    break
            else:
                continue
            break

    # Check 5: Parent company / ownership structure
    if entity.parent_company or entity.ownership_structure:
        parent_lower = _normalize(entity.parent_company)
        own_lower = _normalize(entity.ownership_structure)
        combined = parent_lower + " " + own_lower
        for std_key, aliases in _COUNTRY_OF_CONCERN_ALIASES.items():
            for alias in aliases:
                if len(alias) > 3 and alias in combined:
                    coc_label = _COUNTRY_OF_CONCERN_NAMES.get(std_key, std_key)
                    assessment.covered_person_reasons.append(
                        f"Ownership structure or parent company linked to {coc_label}."
                    )
                    has_moderate_signal = True
                    assessment.confidence = max(assessment.confidence, 0.75)
                    assessment.missing_information.append(
                        f"Please clarify the control relationship between '{entity.entity_name}' "
                        f"and the {coc_label}-linked entity."
                    )
                    break
            else:
                continue
            break

    # Check 6: Access persons — moderate signal, consider residence over nationality
    entity_access_persons = [
        p for p in access_persons
        if p.employer == entity.entity_name or not p.employer
    ]
    for person in entity_access_persons:
        if not person.has_actual_access:
            continue
        # Residence is prioritized over nationality for covered person assessment
        residence_hit, res_key, _ = _match_country_of_concern(person.country_of_residence)
        nationality_hit, nat_key, _ = _match_country_of_concern(person.nationality)

        if residence_hit and res_key != "needs_review":
            coc_label = _COUNTRY_OF_CONCERN_NAMES.get(res_key, res_key)
            reason = (
                f"Access person '{person.person_name}' resides in country of concern "
                f"({person.country_of_residence}, {coc_label}) and has actual data access."
            )
            assessment.covered_person_reasons.append(reason)
            has_moderate_signal = True
            assessment.confidence = max(assessment.confidence, 0.80)
        elif nationality_hit and nat_key != "needs_review":
            coc_label = _COUNTRY_OF_CONCERN_NAMES.get(nat_key, nat_key)
            reason = (
                f"Access person '{person.person_name}' is a national of country of concern "
                f"({person.nationality}, {coc_label}) with actual data access. "
                f"Note: residence is {person.country_of_residence or 'unknown'}."
            )
            assessment.covered_person_reasons.append(reason)
            has_moderate_signal = True
            assessment.confidence = max(assessment.confidence, 0.75)
            assessment.missing_information.append(
                f"Access person '{person.person_name}' has {coc_label} nationality but residence "
                f"in '{person.country_of_residence}'. Please confirm: (1) primary residence; "
                f"(2) nature and scope of access; (3) whether access includes export capability."
            )
        elif (residence_hit and res_key == "needs_review") or (nationality_hit and nat_key == "needs_review"):
            assessment.missing_information.append(
                f"Access person '{person.person_name}' may be associated with a special jurisdiction. "
                f"Please clarify residency, nationality, and access permissions."
            )

    # ── Determine final status ──
    if user_said_not_covered:
        # User override: mark as not_covered but retain warning signals
        assessment.is_covered_person = False
        assessment.covered_person_status = "not_covered"
        if has_strong_signal or has_moderate_signal:
            assessment.covered_person_reasons.append(
                "WARNING: User stated entity is not a covered person, but the system "
                "detected signals suggesting a country-of-concern connection. "
                "Legal review recommended."
            )
            assessment.confidence = 0.60
        return assessment

    if special_jurisdiction_hit and not has_strong_signal:
        assessment.is_covered_person = False  # Not affirmatively covered — needs review
        assessment.covered_person_status = "needs_review"
        assessment.covered_person_reasons.append(special_jurisdiction_detail)
        assessment.confidence = 0.55
        return assessment

    if has_strong_signal:
        assessment.is_covered_person = True
        assessment.covered_person_status = "confirmed" if assessment.confidence >= 0.85 else "inferred"
        return assessment

    if has_moderate_signal:
        assessment.is_covered_person = True
        assessment.covered_person_status = "inferred"
        return assessment

    # No triggers at all
    assessment.is_covered_person = False
    assessment.covered_person_status = "not_covered"
    assessment.confidence = 0.75
    return assessment


def infer_covered_persons(
    entities: list[US14117Entity],
    access_persons: list[US14117AccessPerson],
) -> list[EntityAssessment]:
    """Stage 3: Infer covered person status for all entities."""
    return [infer_covered_person_for_entity(e, access_persons) for e in entities]


# ═════════════════════════════════════════════════════════════════════════
# Stage 4 — Transaction type classification
# ═════════════════════════════════════════════════════════════════════════

def classify_transaction_type(request: US14117Request) -> TransactionAssessment:
    """Stage 4: Classify the transaction type and check EO 14117 applicability."""
    tx_type = _normalize(request.transaction_type)
    tx_desc = _normalize(request.transaction_description)

    assessment = TransactionAssessment(transaction_type=request.transaction_type)

    # Data brokerage detection
    if "data_brokerage" in tx_type or "data_broker" in tx_type:
        assessment.is_data_brokerage = True
    elif _matches_any_keyword(tx_desc, [
        "sale of data", "data sale", "sell data", "selling data",
        "数据交易", "数据出售", "data brokerage",
    ]):
        assessment.is_data_brokerage = True

    return assessment


# ═════════════════════════════════════════════════════════════════════════
# Stage 5 — Prohibited transaction check
# ═════════════════════════════════════════════════════════════════════════

def _evaluate_transaction(
    tx_assessment: TransactionAssessment,
    entity_assessments: list[EntityAssessment],
    data_classifications: list[DataClassification],
    request: US14117Request,
) -> TransactionAssessment:
    """Stages 5+6: Evaluate whether the transaction is prohibited or restricted."""
    tx_assessment.involves_covered_person = any(
        e.is_covered_person for e in entity_assessments
    )
    tx_assessment.involves_bulk_sensitive = any(
        c.threshold_hit and c.doj_category != "not_14117_data"
        for c in data_classifications
    )
    tx_assessment.involves_government_data = any(
        c.doj_category == "government_related_data" or c.is_government_related
        for c in data_classifications
    )

    # ── Stage 5: Prohibited transactions (§100.2) ──
    # 1. Data brokerage involving covered persons
    if tx_assessment.is_data_brokerage and tx_assessment.involves_covered_person:
        tx_assessment.is_prohibited = True
        tx_assessment.prohibition_reasons.append(
            "Data brokerage transaction involving a covered person — "
            "prohibited under EO 14117 §100.2."
        )

    # 2. Government-related data to covered persons
    if tx_assessment.involves_government_data and tx_assessment.involves_covered_person:
        tx_assessment.is_prohibited = True
        tx_assessment.prohibition_reasons.append(
            "Transfer of government-related data to a covered person — "
            "prohibited under EO 14117 §100.2."
        )

    # 3. Bulk human genomic data + data brokerage to covered person
    genomic_hits = [
        c for c in data_classifications
        if c.doj_category == "human_genomic_data" and c.threshold_hit
    ]
    if genomic_hits and tx_assessment.involves_covered_person:
        tx_assessment.is_prohibited = True
        tx_assessment.prohibition_reasons.append(
            "Bulk human genomic data (>100 US persons) involving a covered person — "
            "prohibited under EO 14117 §100.2."
        )

    # ── Stage 6: Restricted transactions (§100.3) ──
    if not tx_assessment.is_prohibited:
        # Vendor/employment/investment agreements + covered person + bulk sensitive
        restricted_types = {
            "vendor_agreement", "employment_agreement", "investment_agreement",
            "cooperative_research", "cloud_remote_access",
        }
        tx_lower = _normalize(tx_assessment.transaction_type)
        is_restricted_type = tx_lower in restricted_types

        if is_restricted_type and tx_assessment.involves_covered_person and tx_assessment.involves_bulk_sensitive:
            tx_assessment.is_restricted = True
            tx_assessment.restriction_reasons.append(
                f"Restricted transaction type ({tx_assessment.transaction_type}) "
                f"involving covered person(s) and bulk sensitive personal data — "
                f"requires security measures under EO 14117 §100.3."
            )
        elif is_restricted_type and tx_assessment.involves_covered_person:
            tx_assessment.is_restricted = True
            tx_assessment.restriction_reasons.append(
                f"Restricted transaction type ({tx_assessment.transaction_type}) "
                f"involving covered person(s) — requires security measures under EO 14117 §100.3."
            )

        # Onward transfer risk
        if request.onward_transfer and tx_assessment.involves_covered_person:
            if not tx_assessment.is_restricted:
                tx_assessment.is_restricted = True
            tx_assessment.restriction_reasons.append(
                "Onward transfer (subprocessor / third-party) detected in combination "
                "with covered person — risk of indirect data access escalation."
            )

    return tx_assessment


# ═════════════════════════════════════════════════════════════════════════
# Stage 7 — Security measures gap analysis
# ═════════════════════════════════════════════════════════════════════════

def _match_measure(req_id: str, measure_name: str, measure_desc: str) -> tuple[bool, str]:
    """Check if a user-provided measure matches a required standard measure.

    Returns (is_match, match_type) where match_type is "exact" | "alias" | "description" | "".
    """
    req_norm = _normalize(req_id)
    name_norm = _normalize(measure_name)
    desc_norm = _normalize(measure_desc or "")

    # Exact match on standard ID
    if req_norm == name_norm or req_norm in name_norm or name_norm in req_norm:
        return True, "exact"

    # Alias matching
    aliases = _SECURITY_MEASURE_ALIASES.get(req_id, [])
    for alias in aliases:
        alias_norm = _normalize(alias)
        if alias_norm in name_norm or name_norm in alias_norm:
            return True, "alias"
        if desc_norm and (alias_norm in desc_norm):
            return True, "description"

    return False, ""


def analyze_security_measures(
    measures: list[US14117SecurityMeasure],
    tx_assessment: TransactionAssessment,
) -> SecurityGapReport:
    """Stage 7: Check which required security measures are present or missing.

    Uses exact matching first, then alias dictionary, then description scanning.
    Planned/"missing" measures are NOT counted as implemented.
    """
    if not tx_assessment.is_restricted:
        return SecurityGapReport(is_compliant=True)

    # Collect implemented measures (status must be exactly "implemented")
    implemented_entries: list[tuple[str, str]] = []  # (normalized_name, description)
    for m in measures:
        if m.status == "implemented":
            implemented_entries.append((_normalize(m.measure_name), _normalize(m.description or "")))

    all_required: list[str] = []
    missing: list[str] = []
    partial_measures: list[str] = []
    implemented: list[str] = []

    for category, measure_list in REQUIRED_SECURITY_MEASURES.items():
        for req_id in measure_list:
            all_required.append(req_id)

            best_match_type = ""
            for name_norm, desc_norm in implemented_entries:
                is_match, match_type = _match_measure(req_id, name_norm, desc_norm)
                if is_match:
                    if match_type == "exact":
                        best_match_type = "exact"
                        break
                    elif match_type == "alias" and best_match_type != "exact":
                        best_match_type = "alias"
                    elif match_type == "description" and best_match_type not in ("exact", "alias"):
                        best_match_type = "description"

            if best_match_type == "exact":
                implemented.append(req_id)
            elif best_match_type in ("alias", "description"):
                partial_measures.append(req_id)
                implemented.append(req_id)  # count as implemented but flag
            else:
                missing.append(req_id)

    return SecurityGapReport(
        required_measures=all_required,
        implemented=implemented,
        missing=missing,
        partial_measures=partial_measures,
        is_compliant=len(missing) == 0,
    )


# ═════════════════════════════════════════════════════════════════════════
# Stage 8 — Traffic light resolution
# ═════════════════════════════════════════════════════════════════════════

def resolve_traffic_light(
    tx_assessment: TransactionAssessment,
    security_gaps: SecurityGapReport,
) -> US14117TrafficLightResult:
    """Stage 8: Determine the final RED / YELLOW / GREEN result.

    RED    = Prohibited transaction detected (§100.2)
    YELLOW = Restricted transaction (§100.3):
             - "blocked": security measures missing, must NOT proceed
             - "controlled": measures implemented, may proceed under monitoring
    GREEN  = No EO 14117 trigger
    """
    if tx_assessment.is_prohibited:
        return US14117TrafficLightResult(
            overall_light="RED",
            summary=(
                "禁止传输：该交易涉及 EO 14117 §100.2 禁止的交易类别。"
                "建议立即停止数据传输并咨询法务团队。"
            ),
            is_prohibited=True,
            prohibition_reasons=tx_assessment.prohibition_reasons,
            required_security_measures=security_gaps.required_measures,
        )

    if tx_assessment.is_restricted:
        has_gaps = len(security_gaps.missing) > 0

        if has_gaps:
            yellow_status = "blocked"
            can_proceed = False
            summary = (
                f"限制性交易（整改前不得进行）：该交易属于 EO 14117 §100.3 限制性交易类别。"
                f"当前存在 {len(security_gaps.missing)} 项安全措施缺口，在全部整改完成并经法务审批前，"
                f"不得继续推进数据传输。建议在 90 天内完成整改。"
            )
        else:
            yellow_status = "controlled"
            can_proceed = True
            summary = (
                "限制性交易（安全措施已落实）：该交易属于 EO 14117 §100.3 限制性交易类别，"
                "但所有必要安全措施已基本落实。可在持续监控、季度审计和合同约束下推进，"
                "但需保持定期复审并随时准备应对法规更新。"
            )

        return US14117TrafficLightResult(
            overall_light="YELLOW",
            summary=summary,
            is_restricted=True,
            restriction_reasons=tx_assessment.restriction_reasons,
            required_security_measures=security_gaps.required_measures,
            missing_security_measures=security_gaps.missing,
            yellow_status=yellow_status,
            can_proceed_conditionally=can_proceed,
        )

    return US14117TrafficLightResult(
        overall_light="GREEN",
        summary=(
            "当前不直接触发 EO 14117 的禁止或限制性规定。"
            "建议持续监控并定期复审。"
        ),
    )


# ═════════════════════════════════════════════════════════════════════════
# Risk matrix builder
# ═════════════════════════════════════════════════════════════════════════

def build_risk_matrix(
    request: US14117Request,
    data_classifications: list[DataClassification],
    entity_assessments: list[EntityAssessment],
    tx_assessment: TransactionAssessment,
) -> list[US14117RiskMatrixRow]:
    """Build the entity × data_item × transaction risk matrix."""
    rows: list[US14117RiskMatrixRow] = []
    classification_by_name = {c.data_item_name: c for c in data_classifications}
    entity_by_name = {e.entity_name: e for e in entity_assessments}

    for entity in request.recipient_entities:
        ea = entity_by_name.get(entity.entity_name)
        if ea is None:
            continue
        cp_status = ea.covered_person_status if ea.covered_person_status != "not_covered" else (
            "confirmed" if ea.is_covered_person and ea.confidence >= 0.9 else (
                "inferred" if ea.is_covered_person else "not_covered"
            )
        )
        cp_reason = "; ".join(ea.covered_person_reasons) if ea.covered_person_reasons else "No triggers detected"

        # Find access persons related to this entity
        entity_access_types = ["direct_entity_relationship"]
        for ap in request.access_persons:
            if ap.employer == entity.entity_name or not ap.employer:
                if ap.has_actual_access:
                    entity_access_types.append(f"person:{ap.person_name}:{ap.access_type or 'direct'}")

        access_method = "; ".join(entity_access_types) if len(entity_access_types) > 1 else entity_access_types[0]

        for data_item in request.data_items:
            dc = classification_by_name.get(data_item.data_item_name)
            if dc is None:
                continue

            # Determine traffic light for this entity-data pair
            if tx_assessment.is_prohibited:
                pair_light = "RED"
                pair_reason = tx_assessment.prohibition_reasons[0] if tx_assessment.prohibition_reasons else "Prohibited transaction"
            elif tx_assessment.is_restricted and dc.threshold_hit and ea.is_covered_person:
                pair_light = "YELLOW"
                pair_reason = tx_assessment.restriction_reasons[0] if tx_assessment.restriction_reasons else "Restricted transaction"
            elif tx_assessment.is_restricted and ea.is_covered_person:
                pair_light = "YELLOW"
                pair_reason = "Restricted transaction with covered person"
            else:
                pair_light = "GREEN"
                pair_reason = "No EO 14117 trigger for this entity-data combination"

            required_actions: list[str] = []
            if pair_light == "RED":
                required_actions = ["立即停止数据传输", "咨询法务团队", "评估替代方案"]
            elif pair_light == "YELLOW":
                required_actions = ["实施必要安全措施", "完成法务审批", "签署修订协议", "建立定期审计机制"]

            rows.append(US14117RiskMatrixRow(
                entity_name=entity.entity_name,
                covered_person_status=cp_status,
                covered_person_reason=cp_reason,
                data_item_name=data_item.data_item_name,
                data_category=dc.doj_category,
                us_person_count=dc.us_person_count,
                threshold=dc.bulk_threshold,
                threshold_hit=dc.threshold_hit,
                transaction_type=tx_assessment.transaction_type,
                access_method=access_method,
                rule_hit_refs=[],
                traffic_light=pair_light,
                reason=pair_reason,
                required_actions=required_actions,
            ))

    return rows


# ═════════════════════════════════════════════════════════════════════════
# Main rule engine entry point
# ═════════════════════════════════════════════════════════════════════════

def generate_clarification_questions(
    entity_assessments: list[EntityAssessment],
    data_classifications: list[DataClassification],
    security_gaps: SecurityGapReport,
) -> list[str]:
    """Generate due-diligence clarification questions based on rule engine gaps."""
    questions: list[str] = []

    # Entity-level questions
    for ea in entity_assessments:
        if ea.missing_information:
            for info in ea.missing_information:
                if info not in questions:
                    questions.append(info)

    # Data classification uncertainty
    for dc in data_classifications:
        if dc.confidence < 0.75 and dc.doj_category != "not_14117_data":
            questions.append(
                f"Data item '{dc.data_item_name}' classified as '{dc.doj_category}' "
                f"with low confidence ({dc.confidence:.0%}). Please verify the correct "
                f"DOJ data category and provide supporting documentation."
            )

    # Security measure gaps with specific requirements
    if security_gaps.missing:
        questions.append(
            f"The following {len(security_gaps.missing)} security measures are required "
            f"but not yet implemented: {', '.join(security_gaps.missing[:5])}"
            f"{'...' if len(security_gaps.missing) > 5 else ''}. "
            f"Please provide implementation timeline and responsible parties."
        )

    if security_gaps.partial_measures:
        questions.append(
            f"The following {len(security_gaps.partial_measures)} measures were matched "
            f"via aliases but may need formal verification: "
            f"{', '.join(security_gaps.partial_measures[:5])}"
            f"{'...' if len(security_gaps.partial_measures) > 5 else ''}. "
            f"Please confirm these measures meet EO 14117 requirements with supporting evidence."
        )

    return questions


def run_rule_engine(request: US14117Request) -> US14117RuleEngineResult:
    """Execute all 8 stages of the EO 14117 rule engine.

    Returns a RuleEngineResult that drives facts, issues, evidence, and chapters.
    """

    # Stage 1: Classify data items
    data_classifications = classify_data_items(request.data_items)

    # Stage 2: Check bulk thresholds (with optional overrides)
    data_classifications = check_bulk_thresholds(
        data_classifications, overrides=request.override_thresholds
    )

    # Stage 3: Infer covered persons
    entity_assessments = infer_covered_persons(
        request.recipient_entities, request.access_persons
    )

    # Stage 4: Classify transaction type
    tx_assessment = classify_transaction_type(request)

    # Stages 5+6: Evaluate prohibited / restricted
    tx_assessment = _evaluate_transaction(
        tx_assessment, entity_assessments, data_classifications, request
    )

    # Stage 7: Security gap analysis
    security_gaps = analyze_security_measures(
        request.security_measures, tx_assessment
    )

    # Stage 8: Traffic light
    traffic_light = resolve_traffic_light(tx_assessment, security_gaps)

    # Per-entity lights
    entity_lights: dict[str, str] = {}
    for ea in entity_assessments:
        if tx_assessment.is_prohibited:
            entity_lights[ea.entity_name] = "RED"
        elif ea.is_covered_person and tx_assessment.is_restricted:
            entity_lights[ea.entity_name] = "YELLOW"
        else:
            entity_lights[ea.entity_name] = "GREEN"

    traffic_light.per_entity_lights = entity_lights

    # Generate clarification questions
    traffic_light.clarification_questions = generate_clarification_questions(
        entity_assessments, data_classifications, security_gaps
    )

    # Build rule hits
    all_rule_hits: list[US14117RuleHit] = []
    for reason in tx_assessment.prohibition_reasons:
        all_rule_hits.append(US14117RuleHit(
            rule_id="EO14117-S100.2-PROHIBITED",
            rule_name="Prohibited Transaction",
            section_ref="§100.2",
            hit=True,
            reason=reason,
        ))
    for reason in tx_assessment.restriction_reasons:
        all_rule_hits.append(US14117RuleHit(
            rule_id="EO14117-S100.3-RESTRICTED",
            rule_name="Restricted Transaction",
            section_ref="§100.3",
            hit=True,
            reason=reason,
        ))
    for c in data_classifications:
        if c.threshold_hit and c.doj_category != "not_14117_data":
            all_rule_hits.append(US14117RuleHit(
                rule_id=f"EO14117-THRESHOLD-{c.doj_category.upper()}",
                rule_name=f"Bulk Threshold Hit: {c.doj_category}",
                section_ref="§100.3",
                hit=True,
                reason=f"{c.data_item_name}: {c.us_person_count} US persons >= {c.bulk_threshold} threshold",
            ))
    for ea in entity_assessments:
        if ea.is_covered_person:
            all_rule_hits.append(US14117RuleHit(
                rule_id=f"EO14117-COVERED-{ea.entity_name.upper().replace(' ', '-')[:40]}",
                rule_name=f"Covered Person ({ea.covered_person_status}): {ea.entity_name}",
                section_ref="§100.1",
                hit=True,
                reason="; ".join(ea.covered_person_reasons),
            ))
    for missing in security_gaps.missing:
        all_rule_hits.append(US14117RuleHit(
            rule_id=f"EO14117-SECGAP-{missing.upper().replace(' ', '-')[:50]}",
            rule_name=f"Security Gap: {missing}",
            section_ref="§100.3",
            hit=True,
            reason=f"Required security measure '{missing}' is missing.",
        ))

    # Build risk matrix
    risk_matrix = build_risk_matrix(
        request, data_classifications, entity_assessments, tx_assessment
    )

    return US14117RuleEngineResult(
        data_classifications=[
            {
                "data_item_name": c.data_item_name,
                "doj_category": c.doj_category,
                "bulk_threshold": c.bulk_threshold,
                "threshold_hit": c.threshold_hit,
                "us_person_count": c.us_person_count,
                "is_government_related": c.is_government_related,
                "confidence": c.confidence,
                "reasoning": c.reasoning,
            }
            for c in data_classifications
        ],
        entity_assessments=[
            {
                "entity_name": e.entity_name,
                "is_country_of_concern": e.is_country_of_concern,
                "country_of_concern_reason": e.country_of_concern_reason,
                "is_covered_person": e.is_covered_person,
                "covered_person_status": e.covered_person_status,
                "covered_person_reasons": e.covered_person_reasons,
                "missing_information": e.missing_information,
                "confidence": e.confidence,
            }
            for e in entity_assessments
        ],
        transaction_classification={
            "transaction_type": tx_assessment.transaction_type,
            "is_data_brokerage": tx_assessment.is_data_brokerage,
            "involves_covered_person": tx_assessment.involves_covered_person,
            "involves_bulk_sensitive": tx_assessment.involves_bulk_sensitive,
            "involves_government_data": tx_assessment.involves_government_data,
            "is_prohibited": tx_assessment.is_prohibited,
            "is_restricted": tx_assessment.is_restricted,
            "prohibition_reasons": tx_assessment.prohibition_reasons,
            "restriction_reasons": tx_assessment.restriction_reasons,
        },
        security_gap_report={
            "required_measures": security_gaps.required_measures,
            "implemented": security_gaps.implemented,
            "missing": security_gaps.missing,
            "partial_measures": security_gaps.partial_measures,
            "is_compliant": security_gaps.is_compliant,
        },
        traffic_light=traffic_light,
        risk_matrix=risk_matrix,
        all_rule_hits=all_rule_hits,
    )
