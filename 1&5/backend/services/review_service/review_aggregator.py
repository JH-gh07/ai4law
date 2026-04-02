from backend.schemas.review import AggregatedReview, ReviewIssue, ReviewSeverity


class ReviewAggregator:
    def aggregate(self, issues: list[ReviewIssue]) -> AggregatedReview:
        deduped = self._dedupe(issues)
        ordered = sorted(deduped, key=lambda issue: (self._severity_rank(issue.severity), issue.title))
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in ordered:
            counts[issue.severity.value] += 1

        if counts["HIGH"] > 0:
            rating = "高风险"
        elif counts["MEDIUM"] >= 2:
            rating = "中风险"
        else:
            rating = "低风险"

        priority_actions: list[str] = []
        if counts["HIGH"]:
            priority_actions.append("优先整改涉及告知同意、数据出境、标准合同备案和责任失衡的高风险条款。")
        if counts["MEDIUM"]:
            priority_actions.append("补强安全措施、权利行使、第三方共享和责任边界等中风险内容。")
        if not priority_actions:
            priority_actions.append("当前未发现明显高风险条款，但仍建议人工复核合同商业条款与实际履约安排。")

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

    def _severity_rank(self, severity: ReviewSeverity) -> int:
        return {ReviewSeverity.HIGH: 0, ReviewSeverity.MEDIUM: 1, ReviewSeverity.LOW: 2}.get(severity, 3)
