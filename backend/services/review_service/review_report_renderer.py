"""Enhanced review report renderer — 7‑9 section professional report.

Expanded from 3 sections (v1) to 7‑9 sections with document profile,
risk assessment, completeness check, detailed issues, remediation roadmap,
legal basis summary, and appendix.
"""

from __future__ import annotations

from backend.schemas.review import (
    AggregatedReview,
    MissingItem,
    ReviewIssue,
    ReviewSeverity,
)


class ReviewReportRenderer:
    """Build section‑based report content from an AggregatedReview.

    Returns a list of (section_title, list_of_paragraphs) tuples
    suitable for the DOCX report generator.
    """

    def build_sections(self, review: AggregatedReview) -> list[tuple[str, list[str]]]:
        """Build all report sections."""
        sections: list[tuple[str, list[str]]] = []

        # 一、执行摘要
        sections.append(
            ("一、执行摘要", [
                review.summary,
                f"总体合规评级：{review.overall_rating}",
                f"风险评分：{review.overall_risk_score}/100",
            ])
        )

        # 二、审查概况与方法
        meta = review.review_metadata
        sections.append(
            ("二、审查概况与方法", [
                f"审查模式：{meta.get('review_mode', '未知')}",
                f"文档类型：{review.document_profile.get('document_type', '未识别')}",
                f"文档名称：{review.document_profile.get('document_title', '未提供')}",
                f"审查条款数：{review.document_profile.get('total_clauses', '0')}",
                f"已分类条款数：{review.document_profile.get('classified_clauses', '0')}",
                f"发现问题总数：{review.document_profile.get('total_issues_found', '0')}",
                f"全局缺失项数：{review.document_profile.get('total_missing_items', '0')}",
                "审查方法说明：系统采用条款切分→多标签分类→LLM深度审查+规则兜底→加权风险评估的自动化流程。当LLM不可用时，将降级为基于规则的审查，报告中会标注审查深度和置信度，请人工复核。",
            ])
        )

        # 三、文档画像
        profile_lines = [
            f"文档类型：{review.document_profile.get('document_type', '未识别')}",
        ]
        if review.clauses_summary:
            profile_lines.append("条款类型分布：")
            for ct, count in review.clauses_summary.items():
                profile_lines.append(f"  - {ct}: {count} 条")
        sections.append(("三、文档画像", profile_lines))

        # 四、整体风险评估
        risk_lines = [
            f"总体风险等级：{review.overall_rating}",
            f"风险评分：{review.overall_risk_score}/100",
            f"高风险问题：{review.issue_counts.get('HIGH', 0)} 项",
            f"中风险问题：{review.issue_counts.get('MEDIUM', 0)} 项",
            f"低风险问题：{review.issue_counts.get('LOW', 0)} 项",
            f"全局缺失项：{len(review.missing_items)} 项",
        ]
        if review.consistency_warnings:
            risk_lines.append("")
            risk_lines.append("跨文档一致性警告：")
            for w in review.consistency_warnings:
                risk_lines.append(f"  - {w}")
        sections.append(("四、整体风险评估", risk_lines))

        # 五、完整性检查结果（全局缺失项）
        missing_lines: list[str] = []
        if review.missing_items:
            high_missing = [m for m in review.missing_items if m.severity == ReviewSeverity.HIGH]
            med_missing = [m for m in review.missing_items if m.severity == ReviewSeverity.MEDIUM]
            low_missing = [m for m in review.missing_items if m.severity == ReviewSeverity.LOW]

            if high_missing:
                missing_lines.append(f"【必须补充】{len(high_missing)} 项：")
                for m in high_missing:
                    missing_lines.extend(self._format_missing_item(m))
            if med_missing:
                missing_lines.append(f"\n【建议补充】{len(med_missing)} 项：")
                for m in med_missing:
                    missing_lines.extend(self._format_missing_item(m))
            if low_missing:
                missing_lines.append(f"\n【优化建议】{len(low_missing)} 项：")
                for m in low_missing:
                    missing_lines.extend(self._format_missing_item(m))
        else:
            missing_lines = ["未发现全局缺失项，文档条款覆盖较完整。"]
        sections.append(("五、完整性检查结果", missing_lines))

        # 六、逐条问题清单
        issue_lines: list[str] = []
        if review.issues:
            for i, issue in enumerate(review.issues, 1):
                issue_lines.extend(self._format_issue(i, issue))
        else:
            issue_lines = ["未发现明显的合规问题。"]
        sections.append(("六、逐条问题清单", issue_lines))

        # 七、优先整改路线图
        sections.append(("七、优先整改路线图", review.priority_actions))

        # 八、法规依据汇总
        citation_lines = self._collect_citations(review.issues)
        sections.append(("八、法规依据汇总", citation_lines or ["未检索到法规依据。"]))

        # 九、附录
        appendix_lines = [
            "审查限制说明：",
            "1. 本报告由自动化审查系统生成，仅供参考，不构成正式法律意见。",
            "2. 基于规则检查的发现（标注 review_method=rule）置信度较低，建议人工复核。",
            "3. 若当前审查未启用LLM深度审查（review_mode=RULE_ONLY），审查结果可能不完整。",
            "4. 全局缺失项检测基于文档类型检查清单，实际缺失情况可能更复杂。",
            "",
            f"审查完成时间：{review.review_metadata.get('review_completed_at', '未知')}",
            f"审查模式：{review.review_metadata.get('review_mode', '未知')}",
            "建议补充材料：",
            "- 数据清单",
            "- 隐私政策（如未上传）",
            "- 合同/协议正式版",
            "- 安全措施说明",
        ]
        sections.append(("九、附录", appendix_lines))

        return sections

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    @staticmethod
    def _format_issue(index: int, issue: ReviewIssue) -> list[str]:
        """Format a single issue into report lines."""
        lines = [
            f"--- 问题 {index} ---",
            f"编号：{issue.issue_id}",
            f"严重程度：{issue.severity.value} | 条款类型：{issue.clause_type.value}",
            f"标题：{issue.title}",
            f"问题类型：{issue.problem_type}",
            f"原文摘录：{issue.original_excerpt}",
            f"风险分析：{issue.risk_analysis}",
        ]
        if issue.citation_sources:
            lines.append(f"法规依据：{'；'.join(issue.citation_sources)}")
        if issue.recommendation:
            lines.append(f"修改建议：{issue.recommendation}")
        if issue.suggested_revision and issue.suggested_revision.suggested_text:
            rev = issue.suggested_revision
            lines.append(f"建议替换：")
            lines.append(f"  原文：{rev.original_text[:200]}")
            lines.append(f"  建议改为：{rev.suggested_text[:200]}")
        if issue.facts_uncertain:
            lines.append(f"⚠️ 存在不确定事实：{issue.uncertainty_rationale or '需用户补充确认'}")
        lines.append(f"审查方法：{issue.review_method.value} | 置信度：{issue.review_confidence}")
        return lines

    @staticmethod
    def _format_missing_item(item: MissingItem) -> list[str]:
        """Format a missing item into report lines."""
        lines = [
            f"  [{item.severity.value}] {item.title}",
            f"    描述：{item.description}",
        ]
        if item.legal_basis:
            lines.append(f"    法规依据：{'；'.join(item.legal_basis)}")
        if item.recommendation:
            lines.append(f"    建议：{item.recommendation}")
        return lines

    @staticmethod
    def _collect_citations(issues: list[ReviewIssue]) -> list[str]:
        """Collect unique citations across all issues."""
        seen: set[str] = set()
        lines: list[str] = []
        for issue in issues:
            for sc in issue.structured_citations:
                citation_str = f"《{sc.source_title}》{sc.article}".strip()
                if citation_str and citation_str not in seen:
                    seen.add(citation_str)
                    snippet = sc.snippet[:120] if sc.snippet else ""
                    lines.append(f"  {citation_str}" + (f"：{snippet}" if snippet else ""))
            for cs in issue.citation_sources:
                if cs and cs not in seen:
                    seen.add(cs)
                    lines.append(f"  {cs}")
        return list(dict.fromkeys(lines))  # dedup
