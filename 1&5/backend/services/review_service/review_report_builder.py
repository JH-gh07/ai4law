from backend.schemas.review import AggregatedReview, ContractType, ReviewReport, ReviewStance


class ReviewReportBuilder:
    def build(
        self,
        filenames: list[str],
        aggregated: AggregatedReview,
        contract_type: ContractType,
        review_stance: ReviewStance,
        custom_rule_text: str,
    ) -> ReviewReport:
        legal_basis = sorted(
            {
                citation
                for issue in aggregated.issues
                for citation in issue.citation_sources
            }
        ) or ["《个人信息保护法》及相关数据出境规则"]

        overview = [
            f"审查文件：{'、'.join(filenames)}",
            f"适用场景：{contract_type.value}",
            f"审查立场：{review_stance.value}",
        ]
        if custom_rule_text:
            overview.append(f"自定义审查规则：{custom_rule_text}")

        return ReviewReport(
            title="数据出境合同合规审查报告",
            file_overview=overview,
            legal_basis=legal_basis,
            overall_rating=aggregated.overall_rating,
            executive_summary=aggregated.summary,
            issues=aggregated.issues,
            priority_actions=aggregated.priority_actions,
        )
