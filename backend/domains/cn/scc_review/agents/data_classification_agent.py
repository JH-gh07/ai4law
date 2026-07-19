"""P0 Agent 2: DataClassificationAgent — field-level identification of PI/SPI/anonymization/de-identification.

Solves: users mislabel fields — marking Hashed_Device_ID as "not personal information"
when it may present re-identification risk; or marking fields as "general PI" when
they may constitute sensitive PI (health preferences, salary data, etc.).

Reference: docs/archive/design-provenance/认证标准合同路径.md Section 2
"""

from __future__ import annotations

from backend.domains.cn.scc_review.agents import SCCAgentBase
from backend.domains.cn.scc_review.rule_engine import check_field_mislabel
from backend.domains.cn.scc_review.schema import DataFieldClassification, DataFieldItem, RiskLevel


class DataClassificationAgent(SCCAgentBase):
    agent_name = "cn_scc_data_classification"
    max_tokens = 600

    def run(self, field: DataFieldItem, related_context: str = "") -> dict:
        """Classify a single data field, checking user labels and re-identification risks.

        The agent handles what rules cannot:
        - Whether a combination of fields (e.g., shopping preferences + health preferences)
          together could infer sensitive status
        - Whether hashing/salting is sufficient to claim anonymization
        - Whether business context changes the classification
        """
        # Rule-based check first
        rule_judgment, rule_reason, rule_risk = check_field_mislabel(field)

        if not self.enabled:
            if rule_judgment:
                return DataFieldClassification(
                    field_name=field.field_name,
                    user_claim=field.user_pii_label or field.user_spi_label or "未标注",
                    agent_judgment=rule_judgment,
                    risk=rule_risk,
                    reason=rule_reason,
                    required_evidence=["哈希算法说明", "重标识化风险评估"] if "hash" in field.field_name.lower() else [],
                    confidence=0.7,
                ).model_dump()
            return DataFieldClassification(
                field_name=field.field_name,
                user_claim=field.user_pii_label or field.user_spi_label or "未标注",
                agent_judgment="potential_personal_information" if _is_likely_pii(field) else "not_personal_information",
                risk=RiskLevel.LOW,
                reason="基于字段名称语义的初步判断",
                confidence=0.5,
            ).model_dump()

        # ── Build LLM prompt ──
        prompt = f"""Classify a data field for cross-border transfer under Chinese PIPL.

FIELD DETAILS:
- Field Name: {field.field_name}
- Description: {field.field_description}
- Sample Value: {field.sample_value[:100]}
- User's PI Label: {field.user_pii_label or "未提供"}
- User's SPI Label: {field.user_spi_label or "未提供"}
- Processing Method: {field.processing_method.value}
- Business Purpose: {field.business_purpose}
- Related Fields: {", ".join(field.related_fields) if field.related_fields else "无"}
- Additional Context: {related_context or "无"}

RULE-BASED PRE-CHECK:
- Rule Judgment: {rule_judgment or "无匹配规则"}
- Rule Reason: {rule_reason or "无"}
- Rule Risk: {rule_risk}

TASKS:
1. Determine if the field constitutes "personal information" under PIPL (can it identify a natural person, alone or combined?)
2. Determine if the field constitutes "sensitive personal information" (health, biometric, religious, political, financial, location tracking, minors, etc.)
3. If user claims "anonymization" but the method is hashing/masking/tokenization, flag as potential mislabel — these are de-identification, not anonymization
4. Assess re-identification risk: can hashed values be reversed via dictionary attack, collision, or correlation?
5. Identify missing evidence needed to support the user's classification claim

Return JSON:
{{
  "field_name": "{field.field_name}",
  "user_claim": "<user's stated classification>",
  "agent_judgment": "personal_information" | "not_personal_information" | "sensitive_personal_information" | "potential_personal_information" | "potential_sensitive_personal_information",
  "risk": "LOW" | "MEDIUM" | "HIGH" | "BLOCKER",
  "reason": "<1-2 sentences explaining the judgment>",
  "required_evidence": ["evidence1", "evidence2"],
  "confidence": 0.0-1.0,
  "mislabel_detected": true | false,
  "reidentification_risk": "LOW" | "MEDIUM" | "HIGH" | "NONE"
}}"""

        result = self._call_llm(prompt) or {
            "field_name": field.field_name,
            "user_claim": field.user_pii_label or field.user_spi_label or "未标注",
            "agent_judgment": rule_judgment or "potential_personal_information",
            "risk": rule_risk or "MEDIUM",
            "reason": rule_reason or "Agent不可用，回退至规则判断",
            "required_evidence": [],
            "confidence": 0.4,
            "mislabel_detected": bool(rule_judgment),
            "reidentification_risk": "MEDIUM" if field.processing_method.value == "hashed" else "NONE",
        }

        result.setdefault("field_name", field.field_name)
        result.setdefault("user_claim", field.user_pii_label or "未标注")
        result.setdefault("risk", "MEDIUM")
        result.setdefault("confidence", 0.5)
        return result


def _is_likely_pii(field: DataFieldItem) -> bool:
    """Simple heuristic: does the field name suggest personal information?"""
    pii_indicators = [
        "name", "姓名", "email", "phone", "手机", "id", "身份证",
        "address", "地址", "device", "设备", "ip", "cookie", "location",
        "位置", "bank", "银行", "salary", "薪酬", "contact", "联系人",
    ]
    name_lower = field.field_name.lower()
    desc_lower = field.field_description.lower()
    return any(indicator in name_lower or indicator in desc_lower for indicator in pii_indicators)
