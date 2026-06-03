"""Agent 2 (P1): ClarificationAgent — generate targeted questions for unknown fields.

Trigger: any core field (q1/q2/q5) is "unknown".
Generates 1-3 most critical follow-up questions to resolve ambiguity.
"""

from __future__ import annotations

from backend.modules.diagnosis.agents import DiagAgentBase


class ClarificationAgent(DiagAgentBase):
    agent_name = "diagnosis_clarification"
    max_tokens = 500

    def run(self, unknown_fields: list[str], industry: str = "",
            data_desc: str = "", purpose: str = "",
            ciio_hint: str = "", has_important_data_hint: str = "",
            personal_info_hint: str = "") -> dict:
        """Generate targeted questions to resolve unknown fields.

        unknown_fields: list of field names that are "unknown"
        """
        if not unknown_fields:
            return {
                "questions": [], "priority_field": None,
                "next_action": "no_unknown_fields",
            }

        # ── Priority: most impactful unknown field ──
        priority_order = [
            "q2_has_important_data",   # 最高优先级 — 一旦是yes直接短路
            "q1_is_ciio",              # 第二 — yes → 安全评估
            "q5_no_personal_info",     # 第三 — yes → 豁免
        ]
        priority_field = None
        for field in priority_order:
            if field in unknown_fields:
                priority_field = field
                break
        if priority_field is None and unknown_fields:
            priority_field = unknown_fields[0]

        # ── Heuristic questions ──
        questions = []
        if "q2_has_important_data" in unknown_fields:
            q = "请描述本次出境数据是否属于金融、医疗、汽车、地图、工业、能源等高敏行业数据？是否涉及群体性、区域性、系统性数据？是否已有行业主管部门认定为重要数据？"
            if industry:
                q = f"贵司属于{industry}行业。{q}"
            questions.append({"field": "q2_has_important_data", "question": q})

        if "q1_is_ciio" in unknown_fields:
            q = "贵司运营的信息系统或网络设施是否被主管部门认定或通知为关键信息基础设施(CII)？所属行业是否为能源、交通、水利、金融、公共服务、电子政务等CII重点行业？"
            questions.append({"field": "q1_is_ciio", "question": q})

        if "q5_no_personal_info" in unknown_fields:
            q = "请确认出境数据中是否包含任何可直接或间接识别自然人的信息（如姓名、手机号、身份证号、邮箱、设备ID、车牌等）？数据是否已经过不可逆匿名化处理？"
            questions.append({"field": "q5_no_personal_info", "question": q})

        # ── LLM refinement ──
        agent_result = self._call_llm(
            f"""Generate 1-3 precise follow-up questions to resolve these unknown diagnosis fields.

Unknown fields: {unknown_fields}
Industry: {industry or 'unknown'}
Data description: {data_desc or 'not provided'}
Purpose: {purpose or 'not provided'}
Priority field: {priority_field}

Return JSON:
{{
  "questions": [
    {{"field": "q2_has_important_data", "question": "precise question text"}}
  ],
  "priority_field": "q2_has_important_data",
  "next_action": "ask_user|proceed_conservative",
  "conservative_assumption": "if user cannot answer, assume worst case for safety"
}}"""
        )

        if agent_result:
            return agent_result

        return {
            "questions": questions,
            "priority_field": priority_field,
            "next_action": "ask_user" if questions else "proceed_conservative",
            "conservative_assumption": (
                f"若无法确认{priority_field}，将按最保守假设处理"
                if priority_field else "所有关键字段已知，可直接判定"
            ),
        }
