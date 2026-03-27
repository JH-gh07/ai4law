from backend.schemas.review import AggregatedReview, ReviewIssue


class ReviewAggregator:
    def aggregate(self, issues: list[ReviewIssue]) -> AggregatedReview:
        deduped = self._dedupe(issues)
        ordered = sorted(deduped, key=lambda issue: (self._severity_rank(issue.severity.value), issue.title))
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in ordered:
            counts[issue.severity.value] += 1

        if counts["HIGH"] > 0:
            rating = "高风险"
        elif counts["MEDIUM"] >= 2:
            rating = "中风险"
        else:
            rating = "低风险"

        priority_actions = []
        if counts["HIGH"]:
            priority_actions.append("优先整改涉及单独同意、境外接收方信息、数据出境说明等高风险问题。")
        if counts["MEDIUM"]:
            priority_actions.append("补足安全措施、权利行使、数据处理范围等中风险条款。")
        if not priority_actions:
            priority_actions.append("当前未发现明显高风险条款，但仍建议人工复核。")

        return AggregatedReview(
            overall_rating=rating,
            summary=f"共识别 {len(ordered)} 个问题，其中 HIGH {counts['HIGH']} 个、MEDIUM {counts['MEDIUM']} 个、LOW {counts['LOW']} 个。",
            issues=ordered,
            issue_counts=counts,
            priority_actions=priority_actions,
        )

    def _dedupe(self, issues: list[ReviewIssue]) -> list[ReviewIssue]:
        seen: set[tuple[str, str, str]] = set()
        result: list[ReviewIssue] = []
        for issue in issues:
            key = (issue.clause_id, issue.problem_type, issue.title)
            if key in seen:
                continue
            seen.add(key)
            result.append(issue)
        return result

    def _severity_rank(self, severity: str) -> int:
        return {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(severity, 3)
