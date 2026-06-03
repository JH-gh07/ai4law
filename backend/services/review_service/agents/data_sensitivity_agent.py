"""Agent P0-2: DataSensitivityAgent — classify data types into PI/SPI/anonymized/de-identified.

Key capability: distinguish anonymized vs de-identified vs pseudonymized data,
identify sensitive PI from contextual cues beyond keyword matching.
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

# ── Sensitivity inference rules ──
_SENSITIVITY_INFERENCE = {
    "门禁记录": ("行踪轨迹", "可能推断个人行踪轨迹，属于敏感个人信息"),
    "出入记录": ("行踪轨迹", "可能推断个人行踪轨迹"),
    "图书借阅记录": ("可能涉及敏感信息", "可能推断思想、兴趣、健康、宗教等敏感倾向"),
    "消费记录": ("可能涉及财产信息", "可能推断个人财产状况或消费习惯"),
    "支付信息": ("金融账户信息", "明确属于敏感个人信息"),
    "行程轨迹": ("行踪轨迹", "明确属于敏感个人信息"),
    "健康数据": ("医疗健康", "明确属于敏感个人信息"),
    "生物识别": ("生物识别信息", "明确属于敏感个人信息"),
    "学生信息": ("可能涉及未成年人信息", "学生群体可能含14岁以下未成年人"),
    "薪酬": ("可能涉及财产信息", "薪酬数据属于个人财产相关信息"),
    "脱敏": ("个人信息属性待确认", "脱敏不等同于匿名化，需确认去标识化程度"),
    "匿名化": ("匿名化有效性待确认", "需确认是否达到不可逆且无法复原的标准"),
    "设备ID": ("可能为个人信息", "设备ID可能与其他信息结合识别自然人"),
}

_SENSITIVITY_CONCLUSION_TEMPLATES = {
    "explicit_spi": "该数据类别明确属于《个人信息保护法》第28条定义的敏感个人信息",
    "inferred_spi": "该数据类别可能推断出敏感个人信息，需进一步确认",
    "likely_pi": "该数据可能构成个人信息",
    "unclear_anonymization": "声称的匿名化/脱敏处理可能未达到不可逆标准",
    "not_enough_info": "当前信息不足以判断数据敏感性",
}


class DataSensitivityAgent(ReviewAgentBase):
    agent_name = "review_data_sensitivity"
    max_tokens = 500

    def run(self, data_items: list[dict] | None = None,
            full_text: str = "", scenario_notes: str = "") -> dict:
        """Classify each data item's PI/SPI/anonymization status."""
        text = full_text[:8000] if full_text else ""
        items = data_items or []

        classifications: list[dict] = []
        for item in items:
            name = item.get("name", item.get("category", ""))
            desc = item.get("description", item.get("value", ""))
            combined = f"{name} {desc}"

            result = {"item": name or "unknown", "classification": "unknown", "sensitivity": "uncertain", "reason": ""}

            for keyword, (inferred_type, reason) in _SENSITIVITY_INFERENCE.items():
                if keyword in combined:
                    result["classification"] = inferred_type
                    result["reason"] = reason
                    if inferred_type in ("行踪轨迹", "金融账户信息", "医疗健康", "生物识别信息"):
                        result["sensitivity"] = "sensitive_personal_information"
                    elif "敏感" in inferred_type:
                        result["sensitivity"] = "possible_sensitive"
                    elif "个人信息" in inferred_type:
                        result["sensitivity"] = "personal_information"
                    else:
                        result["sensitivity"] = "uncertain"
                    break

            # Check anonymization signals
            if "匿名化" in combined or "anonym" in combined.lower():
                if "不可逆" not in combined and "无法复原" not in combined and "irreversible" not in combined.lower():
                    result["sensitivity"] = "anonymization_unverified"
                    result["reason"] += "；声称匿名化但缺少不可逆性证明"
            if "脱敏" in combined and "不可逆" not in combined:
                result["sensitivity"] = "de_identification_unclear"
                result["reason"] += "；脱敏不等于匿名化，可能仍属个人信息"

            classifications.append(result)

        # Check document text for data types mentioned
        if not classifications and text:
            for keyword in _SENSITIVITY_INFERENCE:
                if keyword in text:
                    inferred, reason = _SENSITIVITY_INFERENCE[keyword]
                    classifications.append({
                        "item": keyword, "classification": inferred,
                        "sensitivity": "possible_sensitive" if "敏感" in inferred else "personal_information",
                        "reason": reason, "detected_in_text": True,
                    })

        # ── Agent refinement ──
        agent = self._call_llm(
            f"""Classify the sensitivity of the following data items under Chinese PIPL.

Data items: {classifications}
Document context: {text[:2000]}
Scenario: {scenario_notes[:500]}

Return JSON:
{{
  "has_spi": true|false,
  "has_anonymization_gap": true|false,
  "classifications": [
    {{"item": "...", "classification": "...", "sensitivity": "spi|pi|possible_sensitive|unclear|not_pi", "reason": "..."}}
  ],
  "summary": "<one sentence>",
  "risk_level": "HIGH|MEDIUM|LOW"
}}"""
        )
        if agent:
            return agent

        has_spi = any(c["sensitivity"] == "sensitive_personal_information" for c in classifications)
        return {
            "has_spi": has_spi,
            "has_anonymization_gap": any("anonymization" in c.get("sensitivity", "") for c in classifications),
            "classifications": classifications,
            "summary": f"识别到{'敏感个人信息' if has_spi else '个人信息'}相关数据类型" if classifications else "未识别到明确的数据类别",
            "risk_level": "HIGH" if has_spi else "MEDIUM",
        }
