"""Agent 3: NecessityProportionalityAgent — assess whether each processing step is necessary, proportionate, and data-minimal.

Solves: the system cannot simply write "user considers this necessary". A qualified DPIA must
point out which processing is necessary, which is questionable, which data items are excessive,
and what less-intrusive alternatives exist.

Reference: doc/tmp/dpia Section 4 — GDPR Article 35(7)(b)
"""

from __future__ import annotations

from backend.modules.dpia.agents import DPIAAgentBase
from backend.modules.dpia.schema import NecessityFinding, NecessityFindings


class NecessityProportionalityAgent(DPIAAgentBase):
    agent_name = "dpia_necessity_proportionality"
    max_tokens = 1200

    def run(
        self,
        project_goal: str = "",
        processing_activity_pack: dict | None = None,
        lawful_basis: list[str] | None = None,
        data_categories: list[str] | None = None,
    ) -> dict:
        """Assess necessity and proportionality of each processing step.

        Returns structured NecessityFindings output.
        """
        proc = processing_activity_pack or {}
        lawful_basis = lawful_basis or []
        data_categories = data_categories or []

        if not self.enabled:
            return _rule_based_necessity_check(project_goal, proc, lawful_basis, data_categories)

        steps_text = _format_steps(proc.get("processing_steps", []))
        categories_text = ", ".join(data_categories) if data_categories else "未提供"
        basis_text = ", ".join(lawful_basis) if lawful_basis else "未提供"

        prompt = f"""Assess necessity and proportionality of data processing under GDPR Article 35(7)(b).

PROJECT GOAL: {project_goal or "未提供"}
LAWFUL BASIS: {basis_text}
DATA CATEGORIES: {categories_text}

PROCESSING STEPS:
{steps_text}

TASKS:
1. For each processing step, determine if it is NECESSARY for the stated purpose or QUESTIONABLE
2. Identify EXCESSIVE data items that are not needed for the purpose
3. Propose LESS INTRUSIVE ALTERNATIVES
4. Check data minimisation compliance

Key pitfalls to detect:
- "Facial expression analysis" / "微表情分析" — rarely necessary for job matching
- "Behaviour tracking" / "点击行为" — usually excessive
- Collecting special category data when non-special-category alternatives exist
- Data retention beyond what is needed for the purpose

Return JSON:
{{
  "agent_name": "NecessityProportionalityAgent",
  "necessary_processing": [
    {{"processing": "<step>", "reason": "<why necessary>"}}
  ],
  "questionable_processing": [
    {{"processing": "<step>", "reason": "<why questionable>"}}
  ],
  "excessive_data_items": ["<item1>", "<item2>"],
  "less_intrusive_alternatives": ["<alternative1>", "<alternative2>"],
  "data_minimisation_recommendations": ["<rec1>"],
  "draft_text": "<2-3 sentence assessment in Chinese>"
}}"""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_necessity_check(project_goal, proc, lawful_basis, data_categories)

        result.setdefault("agent_name", "NecessityProportionalityAgent")
        result.setdefault("necessary_processing", [])
        result.setdefault("questionable_processing", [])
        result.setdefault("excessive_data_items", [])
        result.setdefault("less_intrusive_alternatives", [])
        result.setdefault("data_minimisation_recommendations", [])
        result.setdefault("draft_text", "")
        return result


def _rule_based_necessity_check(
    project_goal: str,
    proc: dict,
    lawful_basis: list[str],
    data_categories: list[str],
) -> dict:
    """Fallback rule-based necessity check."""
    necessary: list[dict] = []
    questionable: list[dict] = []
    excessive: list[str] = []
    alternatives: list[str] = []

    # Check processing steps
    steps = proc.get("processing_steps", [])
    for step in steps:
        step_text = str(step).lower()
        if any(kw in step_text for kw in ["收集", "collection", "简历", "resume", "评估", "assessment"]):
            necessary.append({"processing": str(step)[:120], "reason": "与项目目标的基本实现直接相关"})
        elif any(kw in step_text for kw in ["表情", "expression", "facial", "面部", "微表情"]):
            questionable.append({
                "processing": str(step)[:120],
                "reason": "与岗位胜任力之间的必要关联不足，并可能推断健康状况或情绪状态等敏感信息"
            })
            alternatives.append("取消微表情/面部表情分析功能")
        elif any(kw in step_text for kw in ["行为", "behavior", "tracking", "追踪", "点击", "click"]):
            questionable.append({
                "processing": str(step)[:120],
                "reason": "行为追踪/点击分析通常超出招聘目的所必需的范围"
            })
            alternatives.append("仅收集与岗位直接相关的测试结果，取消行为追踪")

    # Check data categories for excess
    for cat in data_categories:
        cat_lower = cat.lower()
        if any(kw in cat_lower for kw in ["面部", "facial", "生物", "biometric", "指纹", "fingerprint"]):
            excessive.append(cat)
            alternatives.append(f"考虑能否用非敏感替代方案替换'{cat}'")
        if any(kw in cat_lower for kw in ["点击", "click", "行为", "behavior", "浏览", "browsing"]):
            excessive.append(cat)

    draft = "自动化筛选对于处理申请具有一定必要性"
    if questionable:
        draft += "，但部分处理环节必要性不足"
    if excessive:
        draft += "，存在过度收集数据项"
    if alternatives:
        draft += "。建议采取更低侵入性的替代方案"

    return {
        "agent_name": "NecessityProportionalityAgent",
        "necessary_processing": necessary,
        "questionable_processing": questionable,
        "excessive_data_items": excessive,
        "less_intrusive_alternatives": alternatives[:5],
        "data_minimisation_recommendations": ["遵循数据最小化原则，删除非必要数据项"],
        "draft_text": draft,
    }


def _format_steps(steps: list[dict]) -> str:
    if not steps:
        return "（未提供处理步骤）"
    lines = []
    for i, s in enumerate(steps, 1):
        actor = s.get("actor", s.get("step", ""))
        processing = s.get("processing", str(s))
        lines.append(f"{i}. [{actor}] {processing}")
    return "\n".join(lines)
