"""TIA supplementary measure sufficiency checker."""

from __future__ import annotations

import json
from pathlib import Path

from backend.domains.eu.tia.schema import TIAMeasureAssessment, TIAStructuredInput


class TIAMeasureSufficiency:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parent / "data" / "tia_country_riskbook.json"
        self.riskbook = json.loads(path.read_text(encoding="utf-8"))

    def assess(
        self, structured: TIAStructuredInput | None, country_risk_level: str,
    ) -> tuple[list[TIAMeasureAssessment], str]:
        results: list[TIAMeasureAssessment] = []
        overall = "sufficient"

        if structured is None:
            return results, "unknown"

        # Classify each available measure
        if structured.has_secure_enclave and structured.has_key_separation:
            results.append(TIAMeasureAssessment(
                measure_name="secure_enclave_with_key_separation", measure_type="technical_extreme",
                sufficient_for_risk=True, assessment="安全飞地+密钥分离：极强技术措施，可对抗系统性政府访问风险",
            ))
        elif structured.has_end_to_end_encryption and structured.key_managed_in_eu:
            results.append(TIAMeasureAssessment(
                measure_name="e2e_encryption_eu_key_management", measure_type="technical_strong",
                sufficient_for_risk=(country_risk_level not in ("VERY_HIGH",)),
                assessment="端到端加密+欧盟密钥管理：强技术措施，可缓解多数政府访问风险",
            ))
        elif structured.encryption_before_transfer and structured.key_managed_in_eu:
            results.append(TIAMeasureAssessment(
                measure_name="encryption_before_transfer_eu_keys", measure_type="technical_strong",
                sufficient_for_risk=(country_risk_level not in ("VERY_HIGH", "HIGH")),
                assessment="传输前加密+欧盟密钥管理：中等偏强措施，可缓解部分风险",
            ))
        elif structured.encryption_before_transfer:
            results.append(TIAMeasureAssessment(
                measure_name="encryption_before_transfer", measure_type="technical_weak",
                sufficient_for_risk=(country_risk_level in ("LOW",)),
                assessment="传输前加密但密钥未明确由欧盟控制：弱技术措施，不足以对抗政府访问风险",
            ))

        # Contractual measures assessment
        thresholds = self.riskbook.get("measure_sufficiency_thresholds", {})
        country_threshold = thresholds.get(country_risk_level, thresholds.get("MEDIUM", {}))

        if not structured.encryption_before_transfer:
            results.append(TIAMeasureAssessment(
                measure_name="contractual_only", measure_type="contractual",
                sufficient_for_risk=country_threshold.get("contractual_alone_sufficient", False),
                assessment="仅合同/组织措施：面对政府访问风险通常不足",
            ))
            if country_risk_level in ("HIGH", "VERY_HIGH"):
                overall = "insufficient"

        # Determine overall
        min_req = country_threshold.get("minimum_level", "technical_strong")
        measure_levels = {
            "contractual": 0, "organizational": 0,
            "technical_weak": 1, "technical_strong": 2, "technical_extreme": 3,
        }
        max_measure_level = max(
            (measure_levels.get(m.measure_type, 0) for m in results), default=0,
        )
        min_required = measure_levels.get(min_req, 2)

        if max_measure_level >= min_required:
            if country_risk_level == "VERY_HIGH" and max_measure_level < 3:
                overall = "highly_conditional"
            elif country_risk_level == "HIGH" and max_measure_level < 2:
                overall = "conditional"
            else:
                overall = "sufficient"
        elif country_risk_level in ("HIGH", "VERY_HIGH"):
            overall = "insufficient"
        else:
            overall = "conditional"

        return results, overall
