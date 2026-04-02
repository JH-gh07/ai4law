from backend.schemas.review import ReviewReport


class ReviewReportRenderer:
    def build_sections(self, report: ReviewReport) -> list[tuple[str, list[str]]]:
        sections: list[tuple[str, list[str]]] = [
            (report.title, []),
            ("文件概要", report.file_overview),
            ("审查依据", report.legal_basis),
            ("总体合规评级", [report.overall_rating, report.executive_summary]),
            ("优先整改建议", report.priority_actions),
        ]
        issue_lines: list[str] = []
        for issue in report.issues:
            issue_lines.append(
                f"[{issue.severity.value}] {issue.title}\n"
                f"定位：{issue.position.section_path or issue.position.clause_number or issue.clause_id}\n"
                f"原文引用：{issue.original_excerpt}\n"
                f"问题类型：{issue.problem_type}\n"
                f"风险分析：{issue.risk_analysis}\n"
                f"法规依据：{'；'.join(issue.citation_sources)}\n"
                f"修改建议：{issue.recommendation}"
            )
        sections.append(("条款级审查发现", issue_lines or ["未发现明显问题。"]))
        return sections
