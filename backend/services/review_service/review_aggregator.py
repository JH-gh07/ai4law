"""Enhanced review aggregator with weighted scoring, missing items, and consistency."""

from __future__ import annotations

from collections import Counter

from backend.schemas.review import (
    AggregatedReview,
    ClassifiedClause,
    MissingItem,
    ReviewIssue,
    ReviewSeverity,
)
from backend.services.review_service.risk_scorer import RiskScorer
from backend.services.review_service.rulebook_loader import RulebookLoader


class ReviewAggregator:
    """Aggregate review issues into a structured AggregatedReview.

    Enhancements over v1:
    - Accepts missing_items and consistency_warnings
    - Uses RiskScorer for weighted overall_risk_score
    - Score‑based rating (≥70 high, 40-69 medium, <40 low)
    - Generates document_profile and clauses_summary
    - Generates review_metadata
    """

    def __init__(
        self,
        risk_scorer: RiskScorer | None = None,
        rulebook_loader: RulebookLoader | None = None,
    ) -> None:
        self.risk_scorer = risk_scorer or RiskScorer(rulebook_loader)
        self.rulebook = rulebook_loader or RulebookLoader()

    @staticmethod
    def severity_rank(severity: str) -> int:
        return {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(severity, 3)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate(
        self,
        issues: list[ReviewIssue],
        missing_items: list[MissingItem] | None = None,
        consistency_warnings: list[str] | None = None,
        classified_clauses: list[ClassifiedClause] | None = None,
        document_type: str = "other",
        document_title: str | None = None,
        review_mode: str = "llm",
    ) -> AggregatedReview:
        """Aggregate review results into final structured output."""
        missing = missing_items or []
        warnings = consistency_warnings or []

        # 1. Deduplicate and sort
        deduped = self._dedupe(issues)
        ordered = sorted(
            deduped, key=lambda i: (self.severity_rank(i.severity.value), i.title),
        )

        # 2. Count issues by severity
        counts: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in ordered:
            if issue.severity.value in counts:
                counts[issue.severity.value] += 1

        # 3. Score issues and calculate overall risk
        for issue in ordered:
            if issue.risk_score == 0.0:
                issue.risk_score = self.risk_scorer.score_issue(issue)

        overall_score = self.risk_scorer.overall_score(ordered, missing)
        rating = self.risk_scorer.rating_label(overall_score)

        # 4. Generate priority actions
        priority_actions = self._build_priority_actions(counts, missing, warnings)

        # 5. Build document profile and clauses summary
        document_profile = self._build_document_profile(
            document_type, document_title,
            classified_clauses or [],
            len(ordered), len(missing),
        )
        clauses_summary = self._build_clauses_summary(classified_clauses or [])

        # 6. Build review metadata
        import datetime
        review_metadata = {
            "review_completed_at": datetime.datetime.now().isoformat(),
            "review_mode": review_mode,
            "total_issues": len(ordered),
            "total_missing": len(missing),
            "total_warnings": len(warnings),
            "document_type": document_type,
        }

        # 7. Summary text
        summary_parts = [f"共识别 {len(ordered)} 个问题"]
        if missing:
            summary_parts.append(f"{len(missing)} 个全局缺失项")
        summary_parts.append(
            f"其中 HIGH {counts['HIGH']} 个、MEDIUM {counts['MEDIUM']} 个、LOW {counts['LOW']} 个。"
        )

        return AggregatedReview(
            overall_rating=rating,
            overall_risk_score=overall_score,
            summary="".join(summary_parts),
            issues=ordered,
            issue_counts=counts,
            priority_actions=priority_actions,
            missing_items=missing,
            document_profile=document_profile,
            clauses_summary=clauses_summary,
            consistency_warnings=warnings,
            review_metadata=review_metadata,
        )

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _dedupe(issues: list[ReviewIssue]) -> list[ReviewIssue]:
        seen: set[tuple[str, str, str]] = set()
        result: list[ReviewIssue] = []
        for issue in issues:
            key = (issue.clause_id, issue.problem_type, issue.title)
            if key in seen:
                continue
            seen.add(key)
            result.append(issue)
        return result

    # ------------------------------------------------------------------
    # Priority actions
    # ------------------------------------------------------------------

    def _build_priority_actions(
        self,
        counts: dict[str, int],
        missing: list[MissingItem],
        warnings: list[str],
    ) -> list[str]:
        actions: list[str] = []

        if counts.get("HIGH", 0) > 0:
            actions.append(
                f"优先整改 {counts['HIGH']} 项高风险问题，"
                "重点涉及单独同意、境外接收方信息、数据出境说明等内容。"
            )
        if missing:
            high_missing = [m for m in missing if m.severity == ReviewSeverity.HIGH]
            if high_missing:
                actions.append(
                    f"补充 {len(high_missing)} 项全局缺失的必备条款："
                    + "、".join(m.title[:30] for m in high_missing[:3])
                )
        if counts.get("MEDIUM", 0) >= 2:
            actions.append(
                f"关注 {counts['MEDIUM']} 项中风险问题，"
                "补充安全措施、权利行使、数据处理范围等相关条款。"
            )
        if warnings:
            actions.append(f"存在 {len(warnings)} 项跨文档一致性警告，建议人工复核。")
        if not actions:
            actions.append("当前未发现明显高风险问题，但仍建议人工复核。")

        return actions

    # ------------------------------------------------------------------
    # Document profile
    # ------------------------------------------------------------------

    @staticmethod
    def _build_document_profile(
        document_type: str,
        document_title: str | None,
        classified_clauses: list[ClassifiedClause],
        total_issues: int,
        total_missing: int,
    ) -> dict[str, str]:
        profile: dict[str, str] = {
            "document_type": document_type,
            "document_title": document_title or "未提供",
            "total_clauses": str(len(classified_clauses)),
            "classified_clauses": str(
                len([c for c in classified_clauses if c.clause_type.value != "OTHER"])
            ),
            "total_issues_found": str(total_issues),
            "total_missing_items": str(total_missing),
        }
        return profile

    @staticmethod
    def _build_clauses_summary(
        classified_clauses: list[ClassifiedClause],
    ) -> dict[str, int]:
        """Count clause types in the document."""
        counter: Counter[str] = Counter()
        for cc in classified_clauses:
            counter[cc.clause_type.value] += 1
        return dict(counter.most_common(15))
