"""Agent 9: BCRApprovalRiskAgent — review core approval blockers and adjust overall rating.

Prevents average-score dilution of critical requirements:
- EU liable entity missing → HIGH regardless of other scores
- Third-party beneficiary rights missing → HIGH
- BCR type mismatch or incorrect → HIGH
- Binding mechanism unclear → HIGH
"""

from __future__ import annotations

from backend.domains.eu.bcr_review.agents import BCRAgentBase


class BCRApprovalRiskAgent(BCRAgentBase):
    agent_name = "bcr_approval_risk"
    max_tokens = 300

    _CRITICAL_BLOCKERS = {
        "BCR-C-1.2": "第三方受益人权利 (Third-party beneficiary rights)",
        "BCR-C-1.3": "EU 责任主体指定 (EU liable entity designation)",
        "BCR-C-1.1": "法律约束力机制 (Binding mechanism)",
        "BCR-P-1.1": "法律约束力机制 — 处理者 (Binding mechanism — processor)",
    }

    def run(self, findings: list[dict], current_rating: str,
            bcr_type: str = "BCR-C",
            type_consistency: str = "consistent") -> dict:
        """Review findings for core approval blockers that must not be diluted.

        When a critical requirement is MISSING or INCORRECT (severity HIGH),
        the overall rating is forced to HIGH regardless of average score.
        """
        approval_blockers: list[str] = []
        critical_missing: list[str] = []

        for finding in findings:
            req_id = finding.get("requirement_id", "")
            if req_id not in self._CRITICAL_BLOCKERS:
                continue

            status = finding.get("coverage_status", finding.get("risk_level", ""))
            severity = finding.get("risk_level", finding.get("severity_if_missing", "MEDIUM"))

            is_blocking = (
                status in ("MISSING", "INCORRECT", "VAGUE") or
                severity == "HIGH"
            )

            if is_blocking:
                label = self._CRITICAL_BLOCKERS[req_id]
                approval_blockers.append(f"缺失关键要求 [{req_id}]: {label}")
                if status == "MISSING":
                    critical_missing.append(req_id)

        # Also check type consistency
        if type_consistency == "mismatch":
            approval_blockers.append(
                f"BCR 类型声明与实际文档内容不一致 (declared vs actual mismatch)"
            )

        # Determine rating adjustment
        rating_adjustment = current_rating
        if approval_blockers and current_rating != "高风险":
            rating_adjustment = "高风险"
        elif approval_blockers:
            rating_adjustment = "高风险"  # already HIGH, but confirm

        return {
            "approval_blockers": approval_blockers,
            "critical_missing": critical_missing,
            "blocker_count": len(approval_blockers),
            "rating_adjustment": rating_adjustment,
            "original_rating": current_rating,
            "rating_changed": rating_adjustment != current_rating,
        }
