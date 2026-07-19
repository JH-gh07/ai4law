"""Agent 6: DPOConsultationAgent — determine DPO position and whether Art 36 prior consultation is needed.

Solves: sign-off is not boilerplate. DPO opinion must enter conclusions and affect whether
the project can launch and whether supervisory authority consultation is required.

Reference: docs/archive/design-provenance/dpia.md Section 7 — GDPR Articles 35-36
"""

from __future__ import annotations

from backend.domains.eu.dpia.agents import DPIAAgentBase


class DPOConsultationAgent(DPIAAgentBase):
    agent_name = "dpia_dpo_consultation"
    max_tokens = 800

    def run(
        self,
        risk_matrix: list[dict] | None = None,
        mitigation_plan: list[dict] | None = None,
        dpo_opinion: str = "",
        remaining_high_risks: list[str] | None = None,
    ) -> dict:
        """Determine DPO position (approval/conditional/objection) and Art 36 recommendation."""
        risk_matrix = risk_matrix or []
        mitigation_plan = mitigation_plan or []
        remaining_high_risks = remaining_high_risks or []

        if not self.enabled:
            return _rule_based_dpo(risk_matrix, mitigation_plan, dpo_opinion, remaining_high_risks)

        risks_text = _format_risks_summary(risk_matrix)
        mitigation_text = _format_mitigation_summary(mitigation_plan)
        high_text = ", ".join(remaining_high_risks) if remaining_high_risks else "无"

        prompt = f"""Determine the DPO position and prior consultation recommendation for a GDPR DPIA.

RISK MATRIX SUMMARY:
{risks_text}

MITIGATION PLAN SUMMARY:
{mitigation_text}

DPO OPINION: {dpo_opinion or "未提供"}

REMAINING HIGH RISKS: {high_text}

TASKS:
1. Determine DPO position:
   - "approval": all risks addressed, project can proceed
   - "conditional_approval": project can proceed IF specified conditions are met before launch
   - "objection": risks cannot be sufficiently mitigated, project should NOT proceed

2. List specific conditions for conditional_approval

3. Determine if GDPR Article 36 prior consultation is recommended:
   - TRUE if ANY residual risk remains HIGH after mitigation
   - TRUE if special category data + automated decision-making + large scale
   - FALSE if all residual risks are MEDIUM or LOW

4. Explain reasoning

Return JSON:
{{
  "agent_name": "DPOPriorConsultationAgent",
  "dpo_position": "approval" | "conditional_approval" | "objection",
  "conditions": ["condition1", "condition2"],
  "prior_consultation_recommended": true | false,
  "reason": "<1-2 sentence explanation>",
  "draft_text": "<DPO opinion in Chinese for the sign-off section>"
}}

CRITICAL: If conditions cannot reduce residual risk below HIGH, prior_consultation must be true."""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_dpo(risk_matrix, mitigation_plan, dpo_opinion, remaining_high_risks)

        result.setdefault("agent_name", "DPOPriorConsultationAgent")
        result.setdefault("dpo_position", "conditional_approval")
        result.setdefault("conditions", [])
        result.setdefault("prior_consultation_recommended", False)
        result.setdefault("reason", "")
        result.setdefault("draft_text", "")
        return result


def _rule_based_dpo(
    risk_matrix: list[dict],
    mitigation_plan: list[dict],
    dpo_opinion: str,
    remaining_high_risks: list[str],
) -> dict:
    """Fallback rule-based DPO position determination."""
    high_risks = [r for r in risk_matrix if r.get("overall_level") == "HIGH"]
    high_residual = [
        m for m in mitigation_plan if m.get("residual_risk") == "HIGH"
    ]
    planned_only = [
        m for entry in mitigation_plan
        for m in entry.get("measures", [])
        if m.get("status") == "planned"
    ]

    conditions: list[str] = []
    position = "conditional_approval"
    prior_consultation = False

    if high_residual:
        prior_consultation = True
        position = "conditional_approval"
        conditions.append("剩余高风险必须在上线前降至中等以下")

    for measure in planned_only[:3]:
        conditions.append(measure.get("measure", "")[:80])

    if not high_risks:
        position = "approval"

    if remaining_high_risks:
        prior_consultation = True

    if not conditions:
        conditions = ["完成DPIA中所有计划措施的落实和验证"]

    draft = "DPO对项目上线持有条件同意意见"
    if conditions:
        draft += f"，前提是：{'；'.join(conditions[:3])}"
    if prior_consultation:
        draft += "。建议在项目实施前考虑依据GDPR第36条向监管机构进行事先咨询"

    return {
        "agent_name": "DPOPriorConsultationAgent",
        "dpo_position": position,
        "conditions": conditions[:5],
        "prior_consultation_recommended": prior_consultation,
        "reason": f"共{len(high_risks)}项HIGH风险，{len(high_residual)}项HIGH剩余风险，{len(planned_only)}项措施仍为planned状态",
        "draft_text": draft,
    }


def _format_risks_summary(risk_matrix: list[dict]) -> str:
    lines = []
    for r in risk_matrix:
        lines.append(f"- [{r.get('overall_level', '?')}] {r.get('risk_name', '')}")
    return "\n".join(lines) or "无风险"

def _format_mitigation_summary(plan: list[dict]) -> str:
    if not plan:
        return "无缓解计划"
    total_measures = sum(len(e.get("measures", [])) for e in plan)
    residual_high = sum(1 for e in plan if e.get("residual_risk") == "HIGH")
    return f"{len(plan)} risk entries, {total_measures} measures, {residual_high} HIGH residual"
