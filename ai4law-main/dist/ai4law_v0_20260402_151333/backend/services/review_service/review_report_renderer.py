from backend.schemas.review import AggregatedReview


class ReviewReportRenderer:
    def build_sections(self, review: AggregatedReview) -> list[tuple[str, list[str]]]:
        sections: list[tuple[str, list[str]]] = [
            ("文件概要与总体评级", [review.summary, f"总体合规评级：{review.overall_rating}"]),
            ("优先整改建议", review.priority_actions),
        ]
        issue_lines: list[str] = []
        for issue in review.issues:
            issue_lines.append(
                f"[{issue.severity.value}] {issue.title} | 条款类型：{issue.clause_type.value} | "
                f"问题类型：{issue.problem_type} | 原文摘录：{issue.original_excerpt} | "
                f"风险分析：{issue.risk_analysis} | 法规依据：{'；'.join(issue.citation_sources)} | "
                f"修改建议：{issue.recommendation}"
            )
        sections.append(("逐条问题清单", issue_lines or ["未发现明显问题。"]))
        return sections
