"""Agent 9: BCRApprovalRiskAgent — approval blocker review beyond formula."""


from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRApprovalRiskAgent(BCRAgentBase):
    agent_name = "bcr_approval_risk"
    max_tokens = 500

    def run(self, findings: list[dict], rating: str, score: float,
            type_consistency: str, bcr_type: str) -> dict:
        finding_list = "\n".join(
            f"- [{f.get('risk_level','?')}] {f.get('title','?')}: {f.get('finding','')[:120]}"
            for f in findings[:15]
        )
        prompt = f"""Review whether current findings include approval blockers for a {bcr_type} BCR.

Type consistency: {type_consistency}
Current rating: {rating} (score: {score})

Findings:
{finding_list}

Identify which findings would likely cause supervisory authority rejection.
Return JSON:
{{
  "approval_blockers": ["finding title that blocks approval"],
  "rating_adjustment": "HIGH" | "MEDIUM" | "KEEP_CURRENT",
  "adjustment_reason": "<one sentence>",
  "critical_missing": ["requirement_id if wholly absent"],
  "overall_assessment": "<1-2 sentence summary for report>"
}}"""
        result = self._call_llm(prompt) or {
            "approval_blockers": [], "rating_adjustment": "KEEP_CURRENT",
            "adjustment_reason": "Agent unavailable — keeping formula-based rating.",
            "critical_missing": [], "overall_assessment": "",
        }
        result.setdefault("approval_blockers", [])
        result.setdefault("rating_adjustment", "KEEP_CURRENT")
        return result
