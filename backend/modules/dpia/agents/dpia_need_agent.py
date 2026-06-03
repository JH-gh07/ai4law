"""Agent 1: DPIANeedAgent — generate structured DPIA trigger justification from rule signals.

Solves: rules can detect high-risk signals but cannot write quality DPIA trigger rationale.
Example: AI recruitment involves not just "automated decision-making" but candidate profiling,
large-scale processing, video analysis, special category data inference, employment opportunity impact.
The agent explains WHY these factors together constitute a DPIA trigger.

Reference: doc/tmp/dpia Section 2
"""

from __future__ import annotations

from backend.modules.dpia.agents import DPIAAgentBase


class DPIANeedAgent(DPIAAgentBase):
    agent_name = "dpia_need"
    max_tokens = 800

    def run(
        self,
        project_profile: dict | None = None,
        rule_signals: dict | None = None,
        legal_candidates: list[str] | None = None,
    ) -> dict:
        """Generate DPIA need assessment from rule signals and project facts.

        Step A: rule layer identifies high-risk signals (done by DPIANeedDetector)
        Step B: agent reads signals + user facts
        Step C: agent generates "why DPIA is needed" explanation
        Step D: LegalGrounding binds GDPR Art 35 / WP248
        Step E: output enters generation_basis_pack.section["need_identification"]
        """
        project_profile = project_profile or {}
        rule_signals = rule_signals or {}
        legal_candidates = legal_candidates or ["GDPR Article 35", "WP29 WP248 rev.01"]

        if not self.enabled:
            return _rule_based_need(project_profile, rule_signals, legal_candidates)

        proj_text = _format_project(project_profile)
        signals_text = _format_signals(rule_signals)
        legal_text = ", ".join(legal_candidates)

        prompt = f"""Determine whether a DPIA is required under GDPR Article 35 and WP248 criteria.

PROJECT PROFILE:
{proj_text}

RULE SIGNALS DETECTED:
{signals_text}

LEGAL REFERENCES: {legal_text}

TASK:
1. Confirm whether DPIA is required
2. For each triggered signal, write a specific reason linked to project facts
3. Generate a draft text paragraph for the DPIA's "need identification" section
4. Bind GDPR Art 35 and WP248 criteria

Consider that multiple signals together amplify risk — e.g., "automated decision-making + large scale + special category inference" is stronger than any single signal.

Return JSON:
{{
  "agent_name": "DPIANeedAgent",
  "dpia_required": true | false,
  "trigger_reasons": [
    {{
      "type": "automated_decision_making" | "large_scale_processing" | "special_category_inference" | "systematic_monitoring" | "new_technology" | "vulnerable_subjects" | "data_matching" | "rights_impact",
      "fact_refs": ["FACT-xxx"],
      "reason": "<specific explanation linked to project facts, 1-2 sentences Chinese>"
    }}
  ],
  "draft_text": "<1 paragraph in Chinese explaining why DPIA is needed>",
  "legal_basis_refs": ["GDPR_ART35", "WP248_HIGH_RISK_CRITERIA"],
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}}

IMPORTANT: Even if only 1 signal is triggered, explain properly. If >=2 signals triggered, note the cumulative high-risk nature per WP248."""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_need(project_profile, rule_signals, legal_candidates)

        result.setdefault("agent_name", "DPIANeedAgent")
        result.setdefault("dpia_required", bool(rule_signals))
        result.setdefault("trigger_reasons", [])
        result.setdefault("draft_text", "")
        result.setdefault("legal_basis_refs", legal_candidates[:3])
        result.setdefault("confidence", "MEDIUM")
        return result


def _rule_based_need(
    project_profile: dict,
    rule_signals: dict,
    legal_candidates: list[str],
) -> dict:
    """Fallback rule-based DPIA need assessment."""
    trigger_reasons: list[dict] = []

    signal_descriptions = {
        "automated_decision_making": ("系统涉及对个人的自动化评估或决策", ["FACT-automated-decision"]),
        "large_scale_processing": ("预计处理大量数据主体的个人数据", ["FACT-scale"]),
        "special_category_inference": ("可能间接推断特殊类别个人数据", ["FACT-special-category"]),
        "systematic_monitoring": ("涉及对数据主体的系统性监控", ["FACT-monitoring"]),
        "new_technology": ("使用新技术处理个人数据", ["FACT-new-tech"]),
        "vulnerable_subjects": ("涉及弱势数据主体群体", ["FACT-vulnerable"]),
        "data_matching": ("涉及来自多个来源的数据匹配或组合", ["FACT-matching"]),
        "rights_impact": ("处理可能对数据主体权利产生重大影响", ["FACT-rights"]),
    }

    for signal_key, value in rule_signals.items():
        if value and signal_key in signal_descriptions:
            desc, fact_refs = signal_descriptions[signal_key]
            trigger_reasons.append({
                "type": signal_key,
                "fact_refs": fact_refs,
                "reason": desc,
            })

    dpia_required = bool(trigger_reasons)
    num_triggers = len(trigger_reasons)

    if dpia_required:
        draft = f"该项目命中WP248高风险标准中的{num_triggers}项指标"
        if num_triggers >= 2:
            draft += "，符合WP248规定的高风险处理多因素累积标准，应在上线前开展DPIA"
        else:
            draft += "，建议开展DPIA以评估和降低高风险处理对数据主体权利的影响"
    else:
        draft = "基于当前输入信息，该项目暂未命中WP248高风险标准，但仍建议进行初步DPIA筛查"

    return {
        "agent_name": "DPIANeedAgent",
        "dpia_required": dpia_required,
        "trigger_reasons": trigger_reasons,
        "draft_text": draft,
        "legal_basis_refs": legal_candidates[:3] if legal_candidates else ["GDPR_ART35", "WP248"],
        "confidence": "HIGH" if dpia_required else "MEDIUM",
    }


def _format_project(profile: dict) -> str:
    lines = [
        f"Name: {profile.get('project_name', '未知')}",
        f"Goal: {profile.get('project_goal', '未知')}",
        f"Data categories: {profile.get('data_categories', [])}",
        f"Data subjects: {profile.get('data_subject_count', '未知')}",
    ]
    return "\n".join(lines)

def _format_signals(signals: dict) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in signals.items())
