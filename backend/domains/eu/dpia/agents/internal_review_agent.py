"""Agent 8: InternalReviewAgent — generate internal AI review highlighting REAL risks.

Solves: external DPIA draft uses formal language. Users may not see the actual risk picture.
This agent generates a direct, plain-language internal review covering:
  worst risks, unimplemented measures, user_claim_only gaps, launch/delay recommendation.

Reference: docs/archive/design-provenance/dpia.md Section 9
"""

from __future__ import annotations

from backend.domains.eu.dpia.agents import DPIAAgentBase


class InternalReviewAgent(DPIAAgentBase):
    agent_name = "dpia_internal_review"
    max_tokens = 1200

    def run(
        self,
        risk_matrix: list[dict] | None = None,
        mitigation_plan: list[dict] | None = None,
        dpo_decision_pack: dict | None = None,
        user_claim_only_facts: list[str] | None = None,
        issues: list[dict] | None = None,
    ) -> dict:
        """Generate internal AI review text covering 8 sections.

        Output sections (per document Section 9.4):
        一、总体风险判断
        二、高风险问题
        三、证据不足事项
        四、计划措施与已落实措施差异
        五、DPO 前置条件
        六、是否建议暂缓上线
        七、材料补充优先级
        八、下一步整改建议
        """
        risk_matrix = risk_matrix or []
        mitigation_plan = mitigation_plan or []
        dpo = dpo_decision_pack or {}
        user_claim_facts = user_claim_only_facts or []
        issues = issues or []

        if not self.enabled:
            return _rule_based_internal_review(risk_matrix, mitigation_plan, dpo, user_claim_facts, issues)

        risks_text = _format_risks_full(risk_matrix)
        mit_text = _format_mit_full(mitigation_plan)
        dpo_text = _format_dpo(dpo)
        claims_text = "\n".join(f"- {f}" for f in user_claim_facts[:10]) if user_claim_facts else "无"
        issues_text = _format_issue_list(issues)

        prompt = f"""Generate an INTERNAL AI review for a GDPR DPIA. This is NOT the external report —
it is a candid assessment for the DPIA owner and DPO.

RISK MATRIX:
{risks_text}

MITIGATION PLAN:
{mit_text}

DPO POSITION:
{dpo_text}

USER-CLAIM-ONLY FACTS (证据不足):
{claims_text}

IDENTIFIED ISSUES:
{issues_text}

TASK: Write a 8-section internal review in Chinese:

1. 总体风险判断: overall risk level and whether the project is ready
2. 高风险问题: list the HIGH risks with plain explanation of why they matter
3. 证据不足事项: which claims lack evidence and what this means
4. 计划措施与已落实措施差异: which measures are only "planned" vs actually "implemented"
5. DPO 前置条件: what must be done before launch
6. 是否建议暂缓上线: YES/NO with reasoning
7. 材料补充优先级: what to collect first, ordered by importance
8. 下一步整改建议: concrete next actions

Return JSON:
{{
  "agent_name": "InternalReviewAgent",
  "overall_risk_judgment": "<1-2 sentence overall assessment>",
  "high_risk_issues": ["issue1", "issue2"],
  "insufficient_evidence_items": ["item1", "item2"],
  "planned_vs_implemented_gaps": ["gap1", "gap2"],
  "dpo_preconditions": ["condition1", "condition2"],
  "recommend_delay_launch": true | false,
  "material_supplement_priority": ["priority1", "priority2"],
  "next_steps": ["step1", "step2"],
  "draft_text": "<full internal review in markdown with 8 sections>"
}}

CRITICAL: Be blunt and direct. This is internal — call out risks that the external draft softens."""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_internal_review(risk_matrix, mitigation_plan, dpo, user_claim_facts, issues)

        result.setdefault("agent_name", "InternalReviewAgent")
        result.setdefault("overall_risk_judgment", "")
        result.setdefault("high_risk_issues", [])
        result.setdefault("insufficient_evidence_items", [])
        result.setdefault("planned_vs_implemented_gaps", [])
        result.setdefault("dpo_preconditions", [])
        result.setdefault("recommend_delay_launch", False)
        result.setdefault("material_supplement_priority", [])
        result.setdefault("next_steps", [])
        result.setdefault("draft_text", "")
        return result


def _rule_based_internal_review(
    risk_matrix: list[dict],
    mitigation_plan: list[dict],
    dpo: dict,
    user_claim_facts: list[str],
    issues: list[dict],
) -> dict:
    """Fallback rule-based internal review."""
    high_risks = [r for r in risk_matrix if r.get("overall_level") == "HIGH"]
    high_risk_names = [r.get("risk_name", r.get("risk_id", "")) for r in high_risks]

    planned_measures = []
    implemented_measures = []
    for entry in mitigation_plan:
        for m in entry.get("measures", []):
            if m.get("status") == "planned":
                planned_measures.append(m.get("measure", "")[:80])
            elif m.get("status") == "implemented":
                implemented_measures.append(m.get("measure", "")[:80])

    gaps = []
    if planned_measures:
        gaps.append(f"共{len(planned_measures)}项措施仍为planned状态，尚未落地实施")
    if not implemented_measures:
        gaps.append("未发现已落实(implemented)的缓解措施，所有措施均为计划状态")

    conditions = dpo.get("conditions", [])[:5]
    prior_consultation = dpo.get("prior_consultation_recommended", False)

    recommend_delay = bool(high_risks) or prior_consultation or (len(planned_measures) > 3)

    draft_parts = [
        "一、总体风险判断",
        f"该项目DPIA识别出{len(risk_matrix)}项风险，其中HIGH级别{len(high_risks)}项。总体风险偏{'高' if high_risks else '中'}。",
        "",
        "二、高风险问题",
    ]
    for name in high_risk_names[:5]:
        draft_parts.append(f"- {name}")
    if not high_risk_names:
        draft_parts.append("- 未发现HIGH级别风险")

    draft_parts.extend(["", "三、证据不足事项"])
    for claim in user_claim_facts[:5]:
        draft_parts.append(f"- {claim[:100]}")
    if not user_claim_facts:
        draft_parts.append("- 暂未识别证据不足事项")

    draft_parts.extend(["", "四、计划措施与已落实措施差异"])
    for gap in gaps[:5]:
        draft_parts.append(f"- {gap}")

    draft_parts.extend(["", "五、DPO前置条件"])
    for cond in conditions[:5]:
        draft_parts.append(f"- {cond}")

    draft_parts.extend(["", "六、是否建议暂缓上线"])
    draft_parts.append("建议暂缓上线" if recommend_delay else "可条件性上线")

    draft_parts.extend(["", "七、材料补充优先级"])
    priorities = []
    if user_claim_facts:
        priorities.append("补充关键主张的证据材料（同意记录、制度文件等）")
    if planned_measures:
        priorities.append("落实计划中的缓解措施并提供实施证明")
    if prior_consultation:
        priorities.append("准备监管机构事先咨询材料")
    for p in (priorities or ["保持定期DPIA复评"]):
        draft_parts.append(f"- {p}")

    draft_parts.extend(["", "八、下一步整改建议"])
    if conditions:
        for c in conditions[:3]:
            draft_parts.append(f"- {c}")
    draft_parts.append("- 完成上述条件后重新提交DPIA以供签核")

    return {
        "agent_name": "InternalReviewAgent",
        "overall_risk_judgment": f"共{len(risk_matrix)}项风险，{len(high_risks)}项HIGH，建议{'暂缓' if recommend_delay else '条件性'}上线",
        "high_risk_issues": high_risk_names[:5],
        "insufficient_evidence_items": [f[:100] for f in user_claim_facts[:5]],
        "planned_vs_implemented_gaps": gaps[:5],
        "dpo_preconditions": conditions[:5],
        "recommend_delay_launch": recommend_delay,
        "material_supplement_priority": priorities[:5],
        "next_steps": (conditions[:3] or ["完成DPIA签核流程"]),
        "draft_text": "\n".join(draft_parts),
    }


def _format_risks_full(risks: list[dict]) -> str:
    lines = []
    for r in risks[:8]:
        lines.append(
            f"- [{r.get('overall_level', '?')}] {r.get('risk_name', '')}: "
            f"likelihood={r.get('likelihood','?')}, impact={r.get('impact','?')}. "
            f"Rights: {r.get('affected_rights', [])}"
        )
    return "\n".join(lines) or "无"

def _format_mit_full(plan: list[dict]) -> str:
    lines = []
    for entry in plan[:5]:
        for m in entry.get("measures", [])[:3]:
            lines.append(f"- [{m.get('status', '?')}] {m.get('measure', '')[:100]}")
    return "\n".join(lines) or "无"

def _format_dpo(dpo: dict) -> str:
    if not dpo:
        return "未提供"
    return f"Position={dpo.get('dpo_position','?')}, Conditions={dpo.get('conditions',[])}, Prior Consultation={dpo.get('prior_consultation_recommended','?')}"

def _format_issue_list(issues: list[dict]) -> str:
    if not issues:
        return "无"
    lines = []
    for i in issues[:10]:
        if isinstance(i, dict):
            lines.append(f"- [{i.get('severity', '?')}] {i.get('title', str(i))}")
    return "\n".join(lines) or "无"
