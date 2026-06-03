"""Agent 3 (P2): PIClassifyAgent — assess whether data contains personal / sensitive personal information.

Trigger: q5_no_personal_info == "unknown" OR personal_info_types uncertain.
Handles anonymization / de-identification / re-identifiability edge cases.
"""

from __future__ import annotations

from backend.modules.diagnosis.agents import DiagAgentBase

_DIRECT_IDENTIFIERS = [
    "姓名", "身份证", "手机号", "电话", "邮箱", "email", "地址",
    "车牌", "VIN", "护照", "社保号", "driver license", "passport",
    "name", "phone", "address", "social security",
]

_INDIRECT_IDENTIFIERS = [
    "设备ID", "device id", "订单号", "order number", "IMEI", "IDFA",
    "精确位置", "GPS", "经纬度", "latitude", "longitude",
    "时间戳", "timestamp", "IP地址", "IP address", "cookie",
    "交易记录", "transaction", "浏览记录", "browsing history",
]

_SENSITIVE_INDICATORS = [
    ("健康", "health"), ("医疗", "medical"), ("病历", "patient"),
    ("金融账户", "financial account"), ("银行", "bank"), ("征信", "credit"),
    ("行踪轨迹", "location tracking"), ("精确位置", "precise location"),
    ("生物识别", "biometric"), ("指纹", "fingerprint"), ("人脸", "face"),
    ("未成年人", "minor"), ("儿童", "child"), ("14岁", "under 14"),
    ("宗教信仰", "religion"), ("政治观点", "political"),
]

_ANONYMIZATION_SIGNALS = [
    "不可逆", "irreversible", "无法复原", "cannot be restored",
    "已去除", "removed", "stripped", "脱敏", "de-identified",
    "匿名化", "anonymized", "aggregated", "聚合",
]

_REIDENTIFICATION_RISK = [
    "可重识别", "可关联", "可匹配", "re-identifiable",
    "linkable", "matchable", "间接识别", "indirect identification",
    "假名化", "pseudonymized", "去标识化", "de-identified (not anonymized)",
]


class PIClassifyAgent(DiagAgentBase):
    agent_name = "diagnosis_pi_classify"
    max_tokens = 500

    def run(self, data_desc: str = "", personal_info_types: list[str] | None = None,
            sensitive_info_types: list[str] | None = None,
            anonymization_desc: str = "", processes_personal_info: str = "",
            industry: str = "", use_case: str = "") -> dict:
        """Assess personal info / sensitive info / anonymization status."""
        types = personal_info_types or []
        sens_types = sensitive_info_types or []
        combined = f"{data_desc} {' '.join(types)} {anonymization_desc} {use_case}".lower()

        # ── Direct identifier detection ──
        direct_hits = [kw for kw in _DIRECT_IDENTIFIERS if kw.lower() in combined]
        indirect_hits = [kw for kw in _INDIRECT_IDENTIFIERS if kw.lower() in combined]
        sens_hits = [(cn, en) for cn, en in _SENSITIVE_INDICATORS
                     if cn in combined or en.lower() in combined]

        # ── Anonymization assessment ──
        anon_signals = [s for s in _ANONYMIZATION_SIGNALS if s.lower() in combined]
        reid_risk = [r for r in _REIDENTIFICATION_RISK if r.lower() in combined]

        # ── Personal info judgment ──
        if processes_personal_info == "yes" or types:
            pi_result = "likely_contains_personal_info"
            pi_suggested = "no"  # q5_no_personal_info = no
        elif direct_hits:
            pi_result = "likely_contains_personal_info"
            pi_suggested = "no"
        elif indirect_hits and not anon_signals:
            pi_result = "possible_personal_info"
            pi_suggested = "no"
        elif indirect_hits and anon_signals and not reid_risk:
            pi_result = "likely_anonymized_sufficiently"
            pi_suggested = "yes"
        elif indirect_hits and anon_signals and reid_risk:
            pi_result = "anonymization_uncertain_reid_risk"
            pi_suggested = "no"
        elif anon_signals and not direct_hits and not indirect_hits:
            pi_result = "anonymized_or_no_personal_info"
            pi_suggested = "yes"
        else:
            pi_result = "insufficient_information"
            pi_suggested = "unknown"

        # ── Sensitive info judgment ──
        if sens_types or sens_hits:
            spi_result = "likely_contains_sensitive_pi"
            spi_confidence = 0.85
        elif direct_hits and any(kw in combined for kw in ("健康", "金融", "位置", "生物")):
            spi_result = "possible_sensitive_pi"
            spi_confidence = 0.6
        else:
            spi_result = "unlikely_sensitive_pi"
            spi_confidence = 0.7

        # ── LLM refinement ──
        agent_result = self._call_llm(
            f"""Assess whether the following data contains personal info / sensitive personal info / is sufficiently anonymized.

Data: {data_desc}
Personal info types claimed: {types}
Sensitive types claimed: {sens_types}
Anonymization description: {anonymization_desc}
Heuristic: pi={pi_result}, spi={spi_result}

Return JSON:
{{
  "personal_information_result": "likely_contains|possible|likely_anonymized|insufficient",
  "suggested_q5_no_personal_info": "yes|no|unknown",
  "contains_sensitive_pi": true|false,
  "re_identification_risk": "none|low|medium|high",
  "legal_basis": ["《个人信息保护法》第4条"],
  "risk_note": "<one sentence>",
  "confidence": 0.0-1.0
}}"""
        )

        if agent_result:
            return agent_result

        return {
            "personal_information_result": pi_result,
            "suggested_q5_no_personal_info": pi_suggested,
            "contains_sensitive_pi": sens_types or bool(sens_hits),
            "re_identification_risk": "medium" if reid_risk else ("low" if anon_signals else "high"),
            "direct_identifiers_found": direct_hits[:5],
            "indirect_identifiers_found": indirect_hits[:5],
            "sensitive_indicators_found": [f"{cn}({en})" for cn, en in sens_hits[:5]],
            "anonymization_signals": anon_signals,
            "reid_risk_indicators": reid_risk,
            "legal_basis": ["《个人信息保护法》第4条", "《个人信息保护法》第28条"],
            "risk_note": (
                "存在可重识别风险，匿名化可能不充分" if reid_risk
                else "匿名化处理可能不足以排除个人信息属性" if indirect_hits and anon_signals
                else "数据可能不含个人信息" if pi_suggested == "yes"
                else "建议进一步确认数据类型和匿名化程度"
            ),
            "confidence": max(0.5, 0.9 - 0.1 * len(reid_risk)),
        }
