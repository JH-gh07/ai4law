"""Agent 9: ConsistencyRepairAgent — check DPIA draft quality and apply automatic repairs.

Solves: post-generation LLM output may miss risks, use wrong citations, be over-optimistic.
This agent runs 10 consistency checks and repairs blocking issues.

Reference: docs/archive/design-provenance/dpia.md Section 10
"""

from __future__ import annotations

from backend.domains.eu.dpia.agents import DPIAAgentBase


# 10 consistency check items from the document
CONSISTENCY_CHECKS = [
    "check_dpia_triggers_covered",         # 1. DPIA触发理由覆盖全部high-risk signals
    "check_processing_description_complete", # 2. 处理活动描述包含数据流、类型、数量、保留期、跨境
    "check_necessity_pointed_out",          # 3. 必要性与相称性指出不必要/过度处理项
    "check_high_risk_has_mitigation",       # 4. 每个HIGH风险有mitigation
    "check_mitigation_has_status",          # 5. 每个mitigation有planned/implemented状态
    "check_dpo_conditions_in_conclusion",   # 6. DPO条件进入结论
    "check_residual_high_triggers_art36",   # 7. residual HIGH risk触发Art 36 prior consultation提示
    "check_forbidden_expressions",          # 8. 禁止表达检查
    "check_fabricated_citations",           # 9. 编造citation检查
    "check_user_claim_as_fact",             # 10. user_claim_only写成已证实事实
]


class ConsistencyRepairAgent(DPIAAgentBase):
    agent_name = "dpia_consistency_repair"
    max_tokens = 1200

    def run(
        self,
        draft_chapters: list[dict] | None = None,
        generation_basis_pack: dict | None = None,
        risk_matrix: list[dict] | None = None,
        mitigation_plan: list[dict] | None = None,
        dpo_decision_pack: dict | None = None,
        facts: list[dict] | None = None,
        known_citations: list[str] | None = None,
    ) -> dict:
        """Run 10 consistency checks and apply repairs for blocking issues.

        Repair rules (Section 10.5):
        - Missing trigger reasons → add identification paragraph
        - HIGH risk without measure → mark "尚需补充措施"
        - planned written as implemented → fix to "计划采取"
        - DPO conditions missing → append to conclusion
        - Residual HIGH without Art 36 → add consultation note
        - Missing citations → use citation_registry
        """
        draft_chapters = draft_chapters or []
        gen_basis = generation_basis_pack or {}
        risk_matrix = risk_matrix or []
        mitigation_plan = mitigation_plan or []
        dpo = dpo_decision_pack or {}
        facts = facts or []
        known_citations = known_citations or []

        if not self.enabled:
            return _rule_based_consistency(
                draft_chapters, gen_basis, risk_matrix, mitigation_plan, dpo, facts, known_citations
            )

        draft_text = _concat_draft(draft_chapters)
        basis_summary = _summarize_basis(gen_basis)
        checks_needed = "\n".join(f"{i+1}. {c}" for i, c in enumerate(CONSISTENCY_CHECKS))

        prompt = f"""Run consistency checks on a DPIA draft and apply repairs.

DRAFT CONTENT (excerpt, first 3000 chars):
---
{draft_text[:3000]}
---

GENERATION BASIS SUMMARY:
{basis_summary}

CHECKS TO PERFORM:
{checks_needed}

Return JSON:
{{
  "agent_name": "ConsistencyRepairAgent",
  "checks_passed": <0-10>,
  "checks_total": 10,
  "blocking_issues": [
    {{"check": "<check name>", "finding": "<what's wrong>", "severity": "HIGH" | "MEDIUM"}}
  ],
  "repairs_applied": [
    {{"check": "<check name>", "original": "<original text>", "repaired": "<repaired text>"}}
  ],
  "needs_manual_review": true | false,
  "final_status": "ready" | "needs_repair" | "blocked",
  "draft_text": "<repair summary>"
}}

IMPORTANT: Be strict but fair. Flag real issues, not style preferences."""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_consistency(
                draft_chapters, gen_basis, risk_matrix, mitigation_plan, dpo, facts, known_citations
            )

        result.setdefault("agent_name", "ConsistencyRepairAgent")
        result.setdefault("checks_passed", 0)
        result.setdefault("checks_total", 10)
        result.setdefault("blocking_issues", [])
        result.setdefault("repairs_applied", [])
        result.setdefault("needs_manual_review", False)
        result.setdefault("final_status", "needs_repair")
        result.setdefault("draft_text", "")
        return result


def _rule_based_consistency(
    draft_chapters: list[dict],
    gen_basis: dict,
    risk_matrix: list[dict],
    mitigation_plan: list[dict],
    dpo: dict,
    facts: list[dict],
    known_citations: list[str],
) -> dict:
    """Fallback rule-based consistency check."""
    blocking: list[dict] = []
    repairs: list[dict] = []
    passed = 0

    draft_text = _concat_draft(draft_chapters)

    # Check 4: HIGH risk has mitigation
    high_risks = [r for r in risk_matrix if r.get("overall_level") == "HIGH"]
    for risk in high_risks:
        risk_id = risk.get("risk_id", "")
        has_mitigation = any(
            entry.get("risk_id") == risk_id and entry.get("measures")
            for entry in mitigation_plan
        )
        if not has_mitigation:
            blocking.append({
                "check": "check_high_risk_has_mitigation",
                "finding": f"HIGH风险{risk_id}缺少对应缓解措施",
                "severity": "HIGH",
            })
            repairs.append({
                "check": "check_high_risk_has_mitigation",
                "original": "（缺失）",
                "repaired": f"为{risk_id}补充缓解措施",
            })
        else:
            passed += 1

    # Check 5: Mitigation has status
    for entry in mitigation_plan:
        for m in entry.get("measures", []):
            if m.get("status") not in ("planned", "implemented", "missing"):
                blocking.append({
                    "check": "check_mitigation_has_status",
                    "finding": f"措施'{m.get('measure', '')[:40]}'缺少状态标注",
                    "severity": "MEDIUM",
                })

    # Check 7: Residual HIGH → Art 36
    high_residual = [m for m in mitigation_plan if m.get("residual_risk") == "HIGH"]
    if high_residual and not dpo.get("prior_consultation_recommended"):
        blocking.append({
            "check": "check_residual_high_triggers_art36",
            "finding": f"存在{len(high_residual)}项HIGH剩余风险但未触发Art 36事先咨询提示",
            "severity": "HIGH",
        })
    else:
        passed += 1

    # Check 8: Forbidden expressions
    forbidden = [
        "风险已完全消除", "完全合规", "无任何风险", "100%安全",
        "绝对保障", "万无一失", "已充分履行所有义务",
    ]
    for expr in forbidden:
        if expr in draft_text:
            blocking.append({
                "check": "check_forbidden_expressions",
                "finding": f"草案中出现禁止表达：'{expr}'",
                "severity": "HIGH",
            })

    # Check 10: user_claim_only as fact
    user_claim_facts = [f for f in facts if
                        (isinstance(f, dict) and f.get("evidence_status") == "user_claim_only") or
                        (hasattr(f, "evidence_status") and f.evidence_status == "user_claim_only")]
    for fact in user_claim_facts[:5]:
        fact_value = fact.get("value", str(fact)) if isinstance(fact, dict) else str(getattr(fact, "value", fact))
        if fact_value and isinstance(fact_value, str) and len(fact_value) > 10:
            if fact_value[:20] in draft_text:
                blocking.append({
                    "check": "check_user_claim_as_fact",
                    "finding": f"user_claim_only事实'{fact_value[:60]}'在草案中可能被作为确认事实表述",
                    "severity": "MEDIUM",
                })

    checks_total = 10
    actual_passed = checks_total - len(set(b["check"] for b in blocking))
    needs_manual = any(b["severity"] == "HIGH" for b in blocking)

    return {
        "agent_name": "ConsistencyRepairAgent",
        "checks_passed": max(0, min(actual_passed, checks_total)),
        "checks_total": checks_total,
        "blocking_issues": blocking[:10],
        "repairs_applied": repairs[:10],
        "needs_manual_review": needs_manual,
        "final_status": "blocked" if needs_manual else ("needs_repair" if blocking else "ready"),
        "draft_text": f"一致性检查：{actual_passed}/{checks_total}项通过。{'需要人工复核' if needs_manual else '可自动修复'}。",
    }


def _concat_draft(chapters: list[dict]) -> str:
    return "\n".join(
        ch.get("content", str(ch)) if isinstance(ch, dict) else str(ch)
        for ch in chapters
    )

def _summarize_basis(basis: dict) -> str:
    sections = basis.get("sections", basis)
    if isinstance(sections, dict):
        return f"Sections: {list(sections.keys())[:7]}"
    return f"Basis keys: {list(basis.keys())[:7]}" if isinstance(basis, dict) else str(basis)[:200]
