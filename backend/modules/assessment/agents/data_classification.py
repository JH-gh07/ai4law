"""Agent 3: Data classification — per-field analysis of data inventory items.

Responsible for:
- Classifying each data item as personal_info / sensitive / important_data / general
- Assessing anonymization/de-identification effectiveness
- Detecting re-identification risks
- Generating conservative expression recommendations

Does NOT: Judge overall compliance or determine regulatory paths.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataItemClassification:
    data_item_name: str
    personal_information_candidate: bool = False
    sensitive_personal_information_candidate: bool = False
    important_data_candidate: str = "unknown"  # yes | no | uncertain
    anonymization_effective: bool = False
    reidentification_risk: str = "low"  # low | medium | high | unknown
    risk_reasoning: list[str] = field(default_factory=list)
    writing_strategy: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8


# Sensitive personal information indicators
_SPI_INDICATORS = [
    "金融账户", "financial account", "bank account", "credit card",
    "行踪轨迹", "precise location", "gps", "经纬度",
    "医疗健康", "health", "medical", "patient", "diagnosis",
    "生物识别", "biometric", "fingerprint", "facial", "dna",
    "宗教信仰", "religious", "political opinion",
    "未成年人", "minor", "child", "children under",
    "身份证号", "id number", "social security", "passport",
    "交易流水", "transaction record", "settlement", "payment history",
    "资产信息", "asset", "wealth", "investment portfolio",
]

# Important data candidate indicators
_IMPORTANT_DATA_INDICATORS = [
    "金融交易", "financial settlement", "支付结算",
    "车辆轨迹", "vehicle track", "vin",
    "地理位置", "geolocation mass",
    "通信记录", "call detail", "communication metadata",
    "能源", "energy", "电力", "power grid",
    "交通", "transportation infrastructure",
    "水利", "water resources",
    "人口健康", "population health", "public health",
]


class DataClassificationAgent:
    """Field-level data classification and re-identification risk assessor."""

    def run(self, data_items: list[dict], industry: str = "", transfer_purpose: str = "") -> list[DataItemClassification]:
        """Classify each data inventory item."""
        results: list[DataItemClassification] = []
        for item in data_items:
            if isinstance(item, dict):
                name = item.get("name", item.get("data_item_name", ""))
                desc = item.get("description", "")
                volume = str(item.get("volume", ""))
                purpose = item.get("necessity", "") or transfer_purpose
            elif hasattr(item, "name"):
                name = item.name
                desc = getattr(item, "description", "")
                volume = str(getattr(item, "volume", ""))
                purpose = getattr(item, "necessity", "") or transfer_purpose
            else:
                continue

            classification = self._classify_single(name, desc, volume, purpose, industry)
            results.append(classification)

        return results

    def _classify_single(self, name: str, desc: str, volume: str, purpose: str, industry: str) -> DataItemClassification:
        search_text = f"{name} {desc} {purpose}".lower()

        is_pii = self._has_indicators(search_text, _SPI_INDICATORS) or any(
            kw in search_text for kw in ("name", "姓名", "email", "邮箱", "phone", "电话", "address", "地址", "identifier", "标识")
        )
        is_spi = self._has_indicators(search_text, _SPI_INDICATORS)
        is_important = self._has_indicators(search_text, _IMPORTANT_DATA_INDICATORS)

        reasoning: list[str] = []
        if is_spi:
            reasoning.append("数据描述包含敏感个人信息特征关键词")
        if is_important:
            reasoning.append("数据描述包含可能的重要数据特征关键词，需结合行业和主管部门认定进一步确认")
        if volume and any(v in volume for v in ("万", "十万", "百万")):
            reasoning.append(f"数据显示较大规模({volume})，影响风险等级")

        # Writing strategy
        forbidden = []
        if is_spi:
            forbidden.append("该数据不涉及敏感个人信息")
        if is_important == "yes":
            forbidden.append("该数据不属于重要数据")

        return DataItemClassification(
            data_item_name=name,
            personal_information_candidate=is_pii,
            sensitive_personal_information_candidate=is_spi,
            important_data_candidate="uncertain" if is_important else "no",
            reidentification_risk="medium" if is_spi else "low",
            risk_reasoning=reasoning,
            writing_strategy={
                "external_expression": (
                    f"数据项'{name}'"
                    f"{'属于或可能属于敏感个人信息' if is_spi else '属于个人信息' if is_pii else '需进一步确认其个人信息属性'}。"
                    f"{'建议在对外报告中采用保守表述，避免直接声称该数据不涉及个人信息或敏感个人信息。' if is_spi or is_pii else ''}"
                ),
                "forbidden_expressions": forbidden,
            },
            confidence=0.85 if is_spi else 0.70,
        )

    @staticmethod
    def _has_indicators(text: str, indicators: list[str]) -> bool:
        return any(ind.lower() in text for ind in indicators)

    def run_with_llm(self, data_items: list[dict], llm_client: Any, industry: str = "", transfer_purpose: str = "") -> list[DataItemClassification]:
        """Enhanced classification with LLM for ambiguous items."""
        results = self.run(data_items, industry, transfer_purpose)

        if not llm_client or not getattr(llm_client, "enabled", False):
            return results

        uncertain = [r for r in results if r.confidence < 0.75]
        if not uncertain:
            return results

        items_json = json.dumps([{"name": r.data_item_name, "risk_reasoning": r.risk_reasoning} for r in uncertain], ensure_ascii=False)
        prompt = (
            f"Analyze these data items for Chinese data export security assessment:\n{items_json}\n\n"
            "For each item, determine if it could be: (a) sensitive personal information under PIPL, "
            "(b) important data under DSL. Return JSON array with fields: data_item_name, "
            "spi_likelihood (low/medium/high), important_data_likelihood (low/medium/high), reasoning."
        )

        try:
            raw = llm_client.chat(system="You are a Chinese data protection law expert.", user=prompt, temperature=0.1, max_tokens=500)
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                for item in parsed:
                    for r in results:
                        if r.data_item_name == item.get("data_item_name"):
                            if item.get("spi_likelihood") == "high":
                                r.sensitive_personal_information_candidate = True
                            if item.get("important_data_likelihood") == "high":
                                r.important_data_candidate = "uncertain"
                            r.confidence = max(r.confidence, 0.75)
        except (json.JSONDecodeError, Exception):
            pass

        return results
