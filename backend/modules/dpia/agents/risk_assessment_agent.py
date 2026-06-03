"""Agent 4: RiskAssessmentAgent — build risk matrix with likelihood, impact, rights affected.

Solves: rules can tag risk labels but cannot assess likelihood × impact × rights.
Smart-city risks (function creep, re-identification, discriminatory planning, mass surveillance,
chilling effects) require contextual reasoning, not keyword matching.

Reference: doc/tmp/dpia Section 5 — GDPR Article 35(7)(c)(d)
"""

from __future__ import annotations

from backend.modules.dpia.agents import DPIAAgentBase


class RiskAssessmentAgent(DPIAAgentBase):
    agent_name = "dpia_risk_assessment"
    max_tokens = 1500

    def run(
        self,
        dpia_need_pack: dict | None = None,
        processing_activity_pack: dict | None = None,
        necessity_findings: dict | None = None,
        user_identified_risks: list[str] | None = None,
        legal_grounding: list[str] | None = None,
    ) -> dict:
        """Build risk matrix: for each risk, assess likelihood, impact, and rights affected.

        Returns structured risk_matrix with RiskMatrixEntry items.
        """
        dpia_need_pack = dpia_need_pack or {}
        proc = processing_activity_pack or {}
        necessity = necessity_findings or {}
        user_identified_risks = user_identified_risks or []
        legal_grounding = legal_grounding or []

        if not self.enabled:
            return _rule_based_risk_assessment(dpia_need_pack, proc, necessity, user_identified_risks)

        need_text = _summarize_need(dpia_need_pack)
        proc_text = _summarize_proc(proc)
        nec_text = _summarize_necessity(necessity)
        user_risks_text = "\n".join(f"- {r}" for r in user_identified_risks) if user_identified_risks else "未提供"
        legal_text = ", ".join(legal_grounding) if legal_grounding else "未提供"

        prompt = f"""Build a risk matrix for a GDPR DPIA.

DPIA NEED: {need_text}

PROCESSING ACTIVITIES:
{proc_text}

NECESSITY FINDINGS:
{nec_text}

USER-IDENTIFIED RISKS: {user_risks_text}

LEGAL GROUNDING: {legal_text}

TASK: For each risk category below that applies, create a risk entry with:
- risk_id: RISK-<topic>
- risk_name: descriptive Chinese name
- description: what the risk is
- affected_rights: which GDPR/data subject rights are affected
- likelihood: LOW | MEDIUM | HIGH
- impact: LOW | MEDIUM | HIGH
- overall_level: LOW | MEDIUM | HIGH (likelihood × impact)
- related_processing_steps: which steps from processing_activity_pack
- reasoning: WHY this level (cite facts, not speculation)

Risk categories to assess (only include those that apply):
1. Algorithmic discrimination (算法歧视)
2. Special category data inference (特殊类别数据推断)
3. Function creep (功能蔓延)
4. Re-identification risk (重识别风险)
5. Mass surveillance / systematic monitoring (大规模监控/寒蝉效应)
6. Data breach / security (数据泄露)
7. Lack of transparency / opaque decision-making (决策不透明)
8. Cross-border transfer risk (跨境传输风险)
9. Vulnerable group impact (弱势群体影响)
10. Automated decision without human intervention (自动化决策无人工干预)

Return JSON:
{{
  "agent_name": "RiskAssessmentAgent",
  "risk_matrix": [
    {{
      "risk_id": "RISK-xxx",
      "risk_name": "...",
      "description": "...",
      "affected_rights": ["right1", "right2"],
      "likelihood": "LOW" | "MEDIUM" | "HIGH",
      "impact": "LOW" | "MEDIUM" | "HIGH",
      "overall_level": "LOW" | "MEDIUM" | "HIGH",
      "related_processing_steps": ["step1"],
      "related_facts": ["fact1"],
      "related_legal_basis": ["GDPR_ART35"],
      "reasoning": "..."
    }}
  ],
  "draft_text": "<overall risk summary in Chinese>"
}}

IMPORTANT:
- Do NOT invent risks that are not supported by the facts
- Include at least 3 risks if processing involves automated decision-making or special category data
- For each HIGH overall_level risk, reasoning must be clear and fact-based"""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_risk_assessment(dpia_need_pack, proc, necessity, user_identified_risks)

        result.setdefault("agent_name", "RiskAssessmentAgent")
        result.setdefault("risk_matrix", [])
        result.setdefault("draft_text", "")
        return result


def _rule_based_risk_assessment(
    dpia_need: dict,
    proc: dict,
    necessity: dict,
    user_risks: list[str],
) -> dict:
    """Fallback rule-based risk assessment."""
    risk_matrix: list[dict] = []
    steps = proc.get("processing_steps", [])
    has_automated = any("评分" in str(s) or "ranking" in str(s).lower() or "自动" in str(s) for s in steps)
    has_special_cat = bool(dpia_need.get("trigger_reasons")) or any(
        "special" in str(s).lower() or "敏感" in str(s) or "特殊类别" in str(s) for s in steps
    )
    has_cross_border = bool(proc.get("cross_border_transfer", {}).get("exists"))

    if has_automated:
        risk_matrix.append({
            "risk_id": "RISK-algorithmic-discrimination",
            "risk_name": "算法歧视性决策风险",
            "description": "自动化评分系统可能因训练数据偏差导致对特定群体的系统性低估或排斥",
            "affected_rights": ["公平就业机会", "非歧视权利", "透明度权利"],
            "likelihood": "MEDIUM",
            "impact": "HIGH",
            "overall_level": "HIGH",
            "related_processing_steps": [s.get("step", "") for s in steps[:3]],
            "related_facts": [],
            "related_legal_basis": ["GDPR_ART35", "GDPR_ART22"],
            "reasoning": "自动化评分直接影响候选人进入面试机会，训练数据偏差可能放大既有招聘歧视",
        })

    if has_special_cat:
        risk_matrix.append({
            "risk_id": "RISK-special-category-inference",
            "risk_name": "特殊类别数据推断风险",
            "description": "处理行为可能间接推断个人的健康状况、种族、宗教信仰或性取向等特殊类别数据",
            "affected_rights": ["隐私权", "非歧视权利", "数据保护权"],
            "likelihood": "MEDIUM",
            "impact": "HIGH",
            "overall_level": "HIGH",
            "related_processing_steps": [s.get("step", "") for s in steps[:2]],
            "related_facts": [],
            "related_legal_basis": ["GDPR_ART9", "GDPR_ART35"],
            "reasoning": "数据组合可能推断特殊类别数据，涉及GDPR第9条保护范围",
        })

    risk_matrix.append({
        "risk_id": "RISK-transparency",
        "risk_name": "决策透明度不足风险",
        "description": "自动化处理逻辑未充分向数据主体解释，可能影响其知情权和异议权",
        "affected_rights": ["知情权", "访问权", "异议权"],
        "likelihood": "MEDIUM",
        "impact": "MEDIUM",
        "overall_level": "MEDIUM",
        "related_processing_steps": [s.get("step", "") for s in steps[:2]],
        "related_facts": [],
        "related_legal_basis": ["GDPR_ART13", "GDPR_ART14", "GDPR_ART22"],
        "reasoning": "自动化系统需提供有意义的解释机制，否则违反透明度要求",
    })

    if has_cross_border:
        risk_matrix.append({
            "risk_id": "RISK-cross-border-transfer",
            "risk_name": "跨境数据传输风险",
            "description": proc.get("cross_border_transfer", {}).get("description", "存在数据跨境传输"),
            "affected_rights": ["数据保护权", "司法救济权"],
            "likelihood": "MEDIUM",
            "impact": "MEDIUM",
            "overall_level": "MEDIUM",
            "related_processing_steps": [],
            "related_facts": [],
            "related_legal_basis": ["GDPR_ART44", "GDPR_ART45", "GDPR_ART46"],
            "reasoning": "跨境传输需确保接收方提供GDPR同等保护水平",
        })

    if not risk_matrix:
        risk_matrix.append({
            "risk_id": "RISK-general",
            "risk_name": "一般数据处理风险",
            "description": "基于当前事实未识别特定高风险，但仍需关注数据保护基本原则的遵守",
            "affected_rights": ["数据保护权"],
            "likelihood": "LOW",
            "impact": "LOW",
            "overall_level": "LOW",
            "related_processing_steps": [],
            "related_facts": [],
            "related_legal_basis": ["GDPR_ART5", "GDPR_ART35"],
            "reasoning": "基于有限输入信息的初始风险评估，建议持续监控",
        })

    return {
        "agent_name": "RiskAssessmentAgent",
        "risk_matrix": risk_matrix,
        "draft_text": f"共识别{len(risk_matrix)}项风险，其中HIGH级别{sum(1 for r in risk_matrix if r['overall_level']=='HIGH')}项，需优先关注并采取缓解措施",
    }


def _summarize_need(pack: dict) -> str:
    if not pack:
        return "未提供"
    triggers = pack.get("trigger_reasons", [])
    if isinstance(triggers, list) and triggers and isinstance(triggers[0], dict):
        triggers = [t.get("type", str(t)) for t in triggers]
    return f"DPIA required: {pack.get('dpia_required', '?')}. Triggers: {triggers}"

def _summarize_proc(proc: dict) -> str:
    steps = proc.get("processing_steps", [])
    return "\n".join(f"- {s.get('step', str(s))}" for s in steps[:5]) or "未提供"

def _summarize_necessity(nec: dict) -> str:
    q = nec.get("questionable_processing", [])
    e = nec.get("excessive_data_items", [])
    return f"Questionable: {len(q)}, Excessive items: {len(e)}"
