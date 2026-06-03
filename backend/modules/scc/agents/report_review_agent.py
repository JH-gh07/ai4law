"""P1 Agent 6: ReportReviewAgent — review generated reports for consistency, completeness, and compliance.

Solves: LLM-generated reports may hallucinate facts, skip risks, use wrong citations,
or confuse concepts. This agent does a post-generation audit across 5 dimensions:
  1. Template completeness — are all required PIPIA sections present?
  2. Fact consistency — does the report introduce facts not in input?
  3. Risk coverage — are all HIGH/BLOCKER issues reflected?
  4. Citation accuracy — does each legal claim have proper basis?
  5. Concept precision — is "certification path" confused with "business certification"?

Reference: doc/tmp/认证标准合同路径 Section 7
"""

from __future__ import annotations

from backend.modules.scc.agents import SCCAgentBase
from backend.modules.scc.schema import ReportReviewProblem, ReportReviewResult


class ReportReviewAgent(SCCAgentBase):
    agent_name = "cn_scc_report_review"
    max_tokens = 1000

    def run(
        self,
        report_text: str,
        facts: list[dict],
        issues: list[dict],
        evidence: list[dict],
        regulations: list[str],
        path_diagnosis: dict | None = None,
        risk_level: str = "MEDIUM",
        template_sections: list[str] | None = None,
    ) -> dict:
        """Review a generated CN SCC report across multiple quality dimensions.

        Returns review_status: "pass" | "needs_repair" | "blocked"
        """
        if not report_text or len(report_text.strip()) < 100:
            return ReportReviewResult(
                review_status="blocked",
                problems=[ReportReviewProblem(
                    type="template_incomplete",
                    text="报告内容为空或过短",
                    reason="报告生成可能失败",
                    repair="重新运行报告生成流程",
                )],
            ).model_dump()

        if not self.enabled:
            return _rule_based_report_review(report_text, facts, issues, regulations, template_sections)

        facts_str = "\n".join(
            f"- [{f.get('source_type', '')}] {f.get('value', f)}" for f in facts[:15]
        ) if facts else "（无事实记录）"

        issues_str = "\n".join(
            f"- [{i.get('severity', '')}] {i.get('title', str(i))}" for i in issues[:15]
        ) if issues else "（无问题记录）"

        regulations_str = "\n".join(f"- {r}" for r in regulations[:10]) if regulations else "（未检索法规）"

        template_str = "\n".join(f"- {s}" for s in (template_sections or [])) if template_sections else "PIPIA标准模板四章结构"

        prompt = f"""Review a CN SCC compliance report for quality and consistency.

REPORT TEXT (excerpt, first 4000 chars):
---
{report_text[:4000]}
---

FACTS USED:
{facts_str}

ISSUES IDENTIFIED:
{issues_str}

RETRIEVED REGULATIONS:
{regulations_str}

TEMPLATE REQUIREMENTS:
{template_str}

PATH DIAGNOSIS: {path_diagnosis.get('recommended_path', '未提供') if path_diagnosis else '未提供'}

FIVE REVIEW DIMENSIONS:
1. Template Completeness: are all required sections covered?
2. Fact Consistency: does the report introduce facts NOT in the facts list? Does it omit issues from the issues list?
3. Risk Coverage: are all HIGH/BLOCKER issues mentioned? Is risk rating consistent with issue severity?
4. Citation Accuracy: does each legal judgment have a regulation basis? Are citations relevant?
5. Concept Precision: is the report free of concept confusion (e.g., treating business certification as PIPL certification)?

Return JSON:
{{
  "review_status": "pass" | "needs_repair" | "blocked",
  "problems": [
    {{
      "type": "unsupported_positive_claim" | "missing_risk_item" | "inconsistent_rating" | "irrelevant_citation" | "template_incomplete" | "concept_confusion",
      "text": "<the problematic text from the report>",
      "reason": "<why it's a problem>",
      "repair": "<concrete fix or rewritten text>"
    }}
  ]
}}

IMPORTANT RULES:
- If the report says "已取得全部用户同意" but evidence is only screenshots → unsupported_positive_claim
- If a HIGH-severity issue from the issues list is not mentioned → missing_risk_item
- If the report uses LOW risk but issues have HIGH items → inconsistent_rating
- If a legal conclusion has no regulation reference → irrelevant_citation
- If required template sections are absent → template_incomplete
- If "认证" refers to business certification (ISO, SOC2) not PIPL certification → concept_confusion"""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_report_review(report_text, facts, issues, regulations, template_sections)

        result.setdefault("review_status", "needs_repair")
        result.setdefault("problems", [])
        return result


def _rule_based_report_review(
    report_text: str,
    facts: list[dict],
    issues: list[dict],
    regulations: list[str],
    template_sections: list[str] | None = None,
) -> dict:
    """Fallback rule-based report review."""
    problems: list[dict] = []

    # Check 1: Template completeness
    sections = template_sections or ["审查依据说明", "总体合规评级", "条款级问题清单", "修订建议与行动计划"]
    for section in sections:
        if section not in report_text:
            problems.append({
                "type": "template_incomplete",
                "text": f"报告缺少'{section}'章节",
                "reason": f"PIPIA模板要求包含{section}",
                "repair": f"补充{section}章节内容",
            })

    # Check 2: Fact consistency — look for overconfident claims
    overconfident_patterns = [
        ("已取得全部", "全部用户"),
        ("完全符合", "完全合规"),
        ("已充分履行", "充分履行"),
        ("已完整实现", "完整实现"),
    ]
    for pattern, concept in overconfident_patterns:
        if pattern in report_text:
            claim_has_evidence = any(
                f.get("evidence_status") in ("verified_evidence", "documented_evidence")
                for f in facts
            )
            if not claim_has_evidence:
                problems.append({
                    "type": "unsupported_positive_claim",
                    "text": f"报告声称'{concept}'",
                    "reason": "输入材料中未提供充分证据支撑此结论",
                    "repair": f"将关于'{concept}'的表述改为谨慎措辞，注明证据完整度",
                })

    # Check 3: Risk coverage
    high_issues = [i for i in issues if i.get("severity") in ("HIGH", "BLOCKER")]
    for issue in high_issues[:5]:
        title = issue.get("title", "")
        if title and title[:10] not in report_text and title[:20] not in report_text:
            problems.append({
                "type": "missing_risk_item",
                "text": f"高风险项'{title}'未在报告中体现",
                "reason": "所有HIGH/BLOCKER级别问题必须在报告中反映",
                "repair": f"在风险分析章节中补充关于'{title}'的评估",
            })

    # Check 4: Citation check
    if regulations and len(regulations) > 0:
        has_citation = any(
            citation[:10] in report_text for citation in regulations
        )
        if not has_citation and len(report_text) > 500:
            problems.append({
                "type": "irrelevant_citation",
                "text": "报告未引用任何检索到的法规条文",
                "reason": "合规报告应有明确的法规依据",
                "repair": "在各章节中嵌入对应的法规条文引用",
            })

    review_status = "blocked" if any(p["type"] == "template_incomplete" for p in problems) else \
                    "needs_repair" if problems else "pass"

    return {
        "review_status": review_status,
        "problems": problems,
    }
