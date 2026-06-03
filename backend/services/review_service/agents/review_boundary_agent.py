"""Agent P2-2: ReviewBoundaryAgent — convert uncertain facts into actionable next-step questions.

Generates prioritized material checklist and clarifies review boundary for the report.
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

_IMPACT_CATEGORIES = {
    "cross_border_determination": {"impact": "直接影响是否构成数据出境", "priority": "P0"},
    "personal_info_determination": {"impact": "直接影响是否属于个人信息", "priority": "P0"},
    "sensitive_pi_determination": {"impact": "直接影响是否为敏感个人信息", "priority": "P0"},
    "important_data_determination": {"impact": "直接影响路径选择", "priority": "P0"},
    "risk_level_impact": {"impact": "影响风险等级判断", "priority": "P1"},
    "revision_completeness": {"impact": "影响修改建议完整性", "priority": "P2"},
}


class ReviewBoundaryAgent(ReviewAgentBase):
    agent_name = "review_boundary"
    max_tokens = 500

    def run(self, uncertain_facts: list[dict] | None = None,
            missing_items: list[dict] | None = None,
            scenario_uncertain: list[str] | None = None) -> dict:
        facts = uncertain_facts or []
        missing = missing_items or []
        uncertain = scenario_uncertain or []

        questions: list[dict] = []
        for f in facts:
            fact_name = f.get("label", f.get("type", str(f)))
            questions.append({
                "priority": "P1", "question": f"请确认: {fact_name}?",
                "impact": "可能影响合规判断",
                "current_assumption": "基于当前信息进行保守假设",
            })

        for m in missing[:5]:
            questions.append({
                "priority": "P0" if m.get("severity") == "HIGH" else "P1",
                "question": f"请补充: {m.get('title', str(m))}",
                "impact": "缺少该材料无法完成审查",
                "current_assumption": "已按缺失材料标注为高风险",
            })

        for u in uncertain[:3]:
            questions.append({
                "priority": "P0", "question": u,
                "impact": "可能改变审查结论",
                "current_assumption": "按最保守假设处理",
            })

        questions.sort(key=lambda q: {"P0": 0, "P1": 1, "P2": 2}.get(q["priority"], 3))

        agent = self._call_llm(
            f"""Generate prioritized follow-up questions and material checklist from review uncertainties.

Uncertain facts: {facts[:5]}
Missing items: {missing[:5]}
Uncertain statements: {uncertain[:3]}

Return JSON:
{{
  "critical_questions": [
    {{"priority": "P0|P1|P2", "question": "...", "impact": "...", "current_assumption": "..."}}
  ],
  "review_boundary_statement": "<explain what conclusions depend on which assumptions>",
  "suggested_materials": ["material1", "material2"],
  "summary": "<one sentence>"
}}"""
        )
        if agent:
            return agent

        boundary = "当前结论基于以下假设: " + ("; ".join(q["current_assumption"] for q in questions[:5]) if questions else "无特殊假设")
        return {
            "critical_questions": questions,
            "review_boundary_statement": boundary,
            "suggested_materials": [m.get("title", str(m)) for m in missing[:3]],
            "summary": f"存在{len(questions)}项需用户确认的不确定事项" if questions else "无需用户补充确认",
        }
