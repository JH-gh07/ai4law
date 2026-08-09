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
        """Derive sign-off fields from structured risks and preserve attribution.

        These fields control whether processing may proceed and whether Article 36
        consultation is required. An LLM must not upgrade a user-entered comment
        into a signed DPO approval, so the critical result is rule-derived.
        """
        risk_matrix = risk_matrix or []
        mitigation_plan = mitigation_plan or []
        remaining_high_risks = remaining_high_risks or []
        return _rule_based_dpo(risk_matrix, mitigation_plan, dpo_opinion, remaining_high_risks)


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

    draft = "系统根据结构化风险记录形成附条件推进建议"
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
        "source_opinion": dpo_opinion,
        "source_opinion_provenance": "user_input" if dpo_opinion.strip() else "missing",
        "decision_basis": "structured_risk_assessment",
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
