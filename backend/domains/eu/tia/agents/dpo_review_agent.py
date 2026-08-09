"""Agent 3: DPOReviewAgent — quality gate ensuring report doesn't soften risk conclusions."""

from __future__ import annotations

from backend.domains.eu.tia.agents import TIAAgentBase


class DPOReviewAgent(TIAAgentBase):
    """Acts as a second-opinion reviewer. Checks whether the report:
    - Correctly reflects the rule engine's risk level
    - Includes mandatory warnings (VERY_HIGH, HIGH)
    - Doesn't soften or dilute compliance conclusions
    - Contains clear DPO position, mandatory conditions, and review plan
    """
    agent_name = "tia_dpo_review"
    max_tokens = 600

    def run(self, route: str, country_risk_level: str, sensitivity: str,
            measure_overall: str, residual_risk: str, issues: list[str],
            chapter_summaries: list[dict]) -> dict:
        ch_block = "\n".join(
            f"- Ch{c.get('no','?')} '{c.get('title','?')}': {c.get('content','')[:200]}..."
            for c in chapter_summaries[:6]
        )
        issues_block = "\n".join(f"- {i}" for i in issues[:10]) or "无"

        prompt = f"""Review a TIA report for compliance quality as a DPO second opinion.

Route: {route}
Country risk: {country_risk_level}
Data sensitivity: {sensitivity}
Measure sufficiency: {measure_overall}
Residual risk after supplementary measures: {residual_risk}
Issues found by rule engine:
{issues_block}

Chapter summaries:
{ch_block}

Return JSON:
{{
  "review_result": "approved|needs_revision|rejected",
  "critical_issues": ["<issue that must be fixed before release>"],
  "risk_softening_detected": true|false,
  "risk_softening_examples": ["<where conclusion is weaker than evidence warrants>"],
  "missing_elements": ["<required section or warning not present>"],
  "dpo_position": "<one sentence DPO stance>",
  "mandatory_conditions": ["<condition that must be met before transfer>"],
  "review_plan_suggestion": "<recommended review interval and triggers>",
  "regulatory_consultation_required": true|false,
  "non_reliance_warning_needed": true|false
}}"""
        fallback = {
            "review_result": "needs_revision" if residual_risk in ("VERY_HIGH", "HIGH") else "approved",
            "critical_issues": issues[:3],
            "risk_softening_detected": False,
            "risk_softening_examples": [],
            "missing_elements": [],
            "dpo_position": "Conditional approval pending resolution of flagged issues." if issues else "No objection.",
            "mandatory_conditions": [],
            "review_plan_suggestion": "Review every 6 months or upon material legal change.",
            "regulatory_consultation_required": residual_risk == "VERY_HIGH",
            "non_reliance_warning_needed": residual_risk == "VERY_HIGH",
        }
        return self._call_llm(prompt) or fallback
