"""BCRRiskAggregator — weighted risk scoring and overall rating for BCR review."""

from __future__ import annotations

from backend.domains.eu.bcr_review.bcr_rulebook_loader import BCRRulebookLoader
from backend.domains.eu.bcr_review.schema import BCRFinding, BCRTypeClassification


class BCRRiskAggregator:
    def __init__(self, rulebook: BCRRulebookLoader | None = None) -> None:
        self.rulebook = rulebook or BCRRulebookLoader()

    def aggregate(
        self, findings: list[BCRFinding], missing_reqs: list[str],
        type_classification: BCRTypeClassification,
    ) -> dict:
        # Score each finding
        for f in findings:
            if f.risk_score == 0.0:
                w = self.rulebook.get_risk_weight(f.requirement_id)
                s = self.rulebook.get_severity_weight(f.risk_level)
                f.risk_score = w * s

        scores = [f.risk_score for f in findings]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Penalty for missing items
        missing_penalty = len([m for m in missing_reqs
                                if any(req.get("severity_if_missing") == "HIGH"
                                       for req in self.rulebook.get_requirements("BCR-C") + self.rulebook.get_shared_requirements()
                                       if req["requirement_id"] == m)]) * 10

        overall_score = min(avg_score + missing_penalty, 100.0)

        # Determine rating
        if type_classification.risk_level == "HIGH" and type_classification.type_consistency == "mismatch":
            rating = "高风险"
        elif overall_score >= 60:
            rating = "高风险"
        elif overall_score >= 30:
            rating = "部分缺失"
        else:
            rating = "基本合规"

        risk_factors = [f.title for f in findings if f.risk_level == "HIGH"]
        if type_classification.risk_level == "HIGH":
            risk_factors.insert(0, f"BCR类型判定: {type_classification.type_consistency}")

        return {
            "overall_rating": rating,
            "overall_score": round(overall_score, 1),
            "risk_factors": risk_factors,
        }
