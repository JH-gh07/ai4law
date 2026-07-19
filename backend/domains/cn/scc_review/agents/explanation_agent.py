"""P2 Agent 9: ExplanationAgent — convert internal trace/facts/issues/evidence into human-readable reasoning chains.

Solves: CN SCC currently has NO trace recording, and even EU SCC's JSON trace is not
user-readable. This agent translates technical pipeline events into a readable
"生成逻辑说明" (Generation Logic Explanation) document.

Reference: docs/archive/design-provenance/认证标准合同路径.md Section 9
"""

from __future__ import annotations

import textwrap

from backend.domains.cn.scc_review.agents import SCCAgentBase
from backend.domains.cn.scc_review.schema import ExplanationResult, ExplanationSegment


class ExplanationAgent(SCCAgentBase):
    agent_name = "cn_scc_explanation"
    max_tokens = 1000

    def run(
        self,
        trace_events: list[dict] | None = None,
        facts: list[dict] | None = None,
        issues: list[dict] | None = None,
        evidence: list[dict] | None = None,
        regulations: list[str] | None = None,
        path_diagnosis: dict | None = None,
        final_report_conclusion: str = "",
    ) -> dict:
        """Generate a human-readable explanation of the system's reasoning process.

        Converts: internal trace → readable decision chain
        Maps: technical fields → business language
        """
        trace_events = trace_events or []
        facts = facts or []
        issues = issues or []
        evidence = evidence or []
        regulations = regulations or []

        if not self.enabled:
            return _rule_based_explanation(
                trace_events, facts, issues, evidence, path_diagnosis, final_report_conclusion
            )

        # Build structured context
        trace_summary = _summarize_trace(trace_events)
        facts_summary = "\n".join(
            f"- {f.get('value', str(f))}" for f in facts[:10]
        ) if facts else "（无结构化事实）"

        issues_summary = "\n".join(
            f"- [{i.get('severity', '?')}] {i.get('title', str(i))}" for i in issues[:10]
        ) if issues else "（无已识别问题）"

        evidence_summary = f"共{len(evidence)}条证据链" if evidence else "（无证据链）"

        path_str = path_diagnosis.get("recommended_path", "未诊断") if path_diagnosis else "未诊断"
        path_rationale = path_diagnosis.get("rationale", "") if path_diagnosis else ""

        prompt = f"""Generate a human-readable "生成逻辑说明" (Generation Logic Explanation) for a CN SCC compliance review.

INTERNAL PIPELINE TRACE:
{trace_summary}

KEY FACTS:
{facts_summary}

IDENTIFIED ISSUES:
{issues_summary}

EVIDENCE STATUS: {evidence_summary}

PATH DIAGNOSIS: {path_str} — {path_rationale}

FINAL CONCLUSION: {final_report_conclusion[:500] if final_report_conclusion else "未提供"}

TASK: Write a 4-6 segment explanation in Chinese that tells the user:
1. What inputs the system received
2. How the path was determined (which thresholds were checked, why)
3. What risks were identified and why
4. What evidence supported or failed to support the conclusions
5. What the final risk rating means
6. What actions are recommended

Each segment should be 1-3 sentences. Map technical fields to business language.
For example:
- "pii_count >= 1,000,000" → "出境个人信息人数达到100万人门槛"
- "has_important_data = False" → "未涉及重要数据"
- "evidence_status: user_claim_only" → "用户声称但未提供支撑证据"

Return JSON:
{{
  "summary": "<2-3 sentence overall summary>",
  "segments": [
    {{
      "step_label": "输入分析",
      "description": "...",
      "source": "表单输入/上传材料"
    }},
    {{
      "step_label": "路径判断",
      "description": "...",
      "source": "规则引擎+路径诊断Agent"
    }}
  ]
}}"""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_explanation(
                trace_events, facts, issues, evidence, path_diagnosis, final_report_conclusion
            )

        result.setdefault("summary", "")
        result.setdefault("segments", [])
        return result


def _rule_based_explanation(
    trace_events: list[dict],
    facts: list[dict],
    issues: list[dict],
    evidence: list[dict],
    path_diagnosis: dict | None = None,
    final_report_conclusion: str = "",
) -> dict:
    """Fallback rule-based explanation generator."""
    segments: list[dict] = []

    # Segment 1: Input analysis
    segments.append({
        "step_label": "输入分析",
        "description": f"系统接收了用户提交的表单数据和{facts and len(facts)}项结构化事实，包括企业信息、出境目的、个人信息规模、合法性基础等内容。",
        "source": "表单输入/上传材料",
    })

    # Segment 2: Path decision
    if path_diagnosis:
        path_map = {
            "standard_contract": "标准合同路径",
            "certification": "认证路径",
            "exemption": "豁免路径",
            "security_assessment": "安全评估路径",
            "uncertain": "路径待定",
        }
        path_label = path_map.get(path_diagnosis.get("recommended_path", ""), "未诊断")
        rationale = path_diagnosis.get("rationale", "")

        triggered = path_diagnosis.get("triggered_thresholds", [])
        threshold_desc = ""
        if triggered:
            threshold_desc = f"检测到以下门槛触发：{'；'.join(triggered)}。"

        segments.append({
            "step_label": "路径判断",
            "description": f"系统首先根据出境人数、敏感个人信息规模、CIIO身份等硬门槛判断{threshold_desc}综合评估后推荐{path_label}。{rationale}",
            "source": "规则引擎+路径诊断Agent",
        })
    else:
        segments.append({
            "step_label": "路径判断",
            "description": "系统根据出境个人信息规模和敏感信息规模判断未触发安全评估门槛，适用标准合同路径。",
            "source": "规则引擎",
        })

    # Segment 3: Risk assessment
    high_count = sum(1 for i in issues if i.get("severity") in ("HIGH", "BLOCKER"))
    medium_count = sum(1 for i in issues if i.get("severity") == "MEDIUM")
    segments.append({
        "step_label": "风险评估",
        "description": f"系统识别出{high_count}项高风险问题和{medium_count}项中风险问题，涵盖数据分类、合法性基础、合同条款、接收方安全能力等维度。",
        "source": "规则引擎+专项审查Agent组",
    })

    # Segment 4: Evidence assessment
    evidence_count = len(evidence)
    if evidence_count > 0:
        segments.append({
            "step_label": "证据核验",
            "description": f"系统对{evidence_count}项用户主张进行了证据匹配，部分主张缺乏充分书面证据支撑，在报告中已标注为谨慎表述或待补充项。",
            "source": "证据核验Agent",
        })
    else:
        segments.append({
            "step_label": "证据核验",
            "description": "系统对用户主张的证据充分性进行了审查，部分关键主张缺乏书面材料支撑，建议补充后再完善报告。",
            "source": "证据核验Agent",
        })

    # Segment 5: Regulation retrieval
    segments.append({
        "step_label": "法规检索",
        "description": "系统根据已识别问题，针对性检索了《个人信息保护法》《个人信息出境标准合同办法》《个人信息安全规范》(GB/T 35273)等相关法律法规和国家标准。",
        "source": "RAG检索规划Agent",
    })

    # Segment 6: Conclusion
    segments.append({
        "step_label": "报告生成与审稿",
        "description": f"基于上述分析生成PIPIA草案，并进行了一致性审稿。{final_report_conclusion[:200] if final_report_conclusion else '报告建议用户在完成材料补充和条款整改后进行备案。'}",
        "source": "报告生成+审稿Agent",
    })

    summary_parts = []
    if path_diagnosis:
        summary_parts.append(f"推荐路径为{path_diagnosis.get('recommended_path', '未诊断')}")
    if issues:
        summary_parts.append(f"共识别{len(issues)}项合规问题")
    summary = "本次系统分析已生成PIPIA草案。" + "，".join(summary_parts) + "。建议结合人工审查后提交备案。"

    return {
        "summary": summary,
        "segments": segments,
    }


def _summarize_trace(trace_events: list[dict]) -> str:
    """Convert raw trace events into a brief summary."""
    if not trace_events:
        return "（无Trace记录）"

    steps = []
    for event in trace_events[:15]:
        event_name = event.get("event", event.get("step", "未知步骤"))
        steps.append(f"• {event_name}")
    return "\n".join(steps) if steps else "（Trace为空）"
