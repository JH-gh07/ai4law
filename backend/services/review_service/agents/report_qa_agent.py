"""Agent P2-3: ReportQAAgent — final quality gate before report rendering.

Checks: HIGH issues in summary, missing items in roadmap, uncertain facts not
written as confirmed, unsupported statements, citation quality, revision quality.
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase


class ReportQAAgent(ReviewAgentBase):
    agent_name = "review_report_qa"
    max_tokens = 600

    def run(self, aggregated_review: dict | None = None,
            chapter_content: list[str] | None = None,
            consistency_warnings: list[str] | None = None) -> dict:
        agg = aggregated_review or {}
        content = chapter_content or []
        warnings = consistency_warnings or []
        combined = " ".join(content) if content else str(agg)

        problems: list[dict] = []

        # 1. HIGH issues in summary
        issues = agg.get("issues", [])
        high_issues = [i for i in issues if str(i.get("severity", "")) in ("HIGH", "BLOCKER")]
        for issue in high_issues[:5]:
            title = str(issue.get("title", ""))[:60]
            if title and title not in combined:
                problems.append({
                    "type": "high_issue_missing_from_report",
                    "issue": title,
                    "repair": "将高风险问题纳入报告正文",
                })

        # 2. Missing items not in roadmap
        missing = agg.get("missing_items", [])
        for m in missing[:5]:
            m_title = str(m.get("title", ""))[:60]
            if m_title and m_title not in combined:
                problems.append({
                    "type": "missing_item_not_in_roadmap",
                    "item": m_title,
                    "repair": "将缺失项纳入整改路线图",
                })

        # 3. Uncertain → confirmed check
        for issue in issues:
            if issue.get("facts_uncertain") and issue.get("review_confidence", 1.0) > 0.85:
                problems.append({
                    "type": "uncertain_fact_written_as_confirmed",
                    "issue": str(issue.get("title", ""))[:60],
                    "repair": f"降低置信度标注或补充不确定说明: {issue.get('uncertainty_rationale', '')[:100]}",
                })

        # 4. Citations check
        issues_with_cites = [i for i in issues if i.get("structured_citations") or i.get("citation_sources")]
        issues_without = [i for i in issues if not i.get("structured_citations") and not i.get("citation_sources")]
        if len(issues_without) > len(issues_with_cites):
            problems.append({
                "type": "low_citation_coverage",
                "description": f"{len(issues_without)}/{len(issues)}个问题缺少法规引用",
                "repair": "为缺少引用的问题补充法规依据",
            })

        # 5. Cross-doc warnings in report
        for w in warnings[:3]:
            if w not in combined:
                problems.append({
                    "type": "cross_doc_warning_missing_from_report",
                    "warning": w[:100],
                    "repair": "将跨文档一致性警告纳入报告",
                })

        quality = "approved"
        if len(problems) >= 3:
            quality = "needs_repair"
        elif len(problems) > 0:
            quality = "approved_with_notes"

        agent = self._call_llm(
            f"""Quality-check a document review report before rendering.

Problems found: {problems}
Report summary: {agg.get('summary', '')[:300]}
Chapter excerpt: {combined[:2000]}

Return JSON:
{{
  "quality_status": "approved|approved_with_notes|needs_repair",
  "problems": [{{"type": "...", "description": "...", "repair": "..."}}],
  "summary": "<one sentence>"
}}"""
        )
        if agent:
            return agent

        return {
            "quality_status": quality,
            "problems": problems,
            "summary": f"报告质检发现{len(problems)}项问题" if problems else "报告质检通过",
        }
