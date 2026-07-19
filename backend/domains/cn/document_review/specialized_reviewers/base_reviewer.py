"""Base class for specialized document‑type reviewers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.schemas.review import ClassifiedClause, ReviewIssue

if TYPE_CHECKING:
    from backend.domains.cn.document_review.rulebook_loader import RulebookLoader


class BaseSpecializedReviewer:
    """Abstract base for document‑type‑specific reviewers.

    Subclasses define additional DSL checks beyond the base rulebook.
    """

    document_type: str = "other"
    specialized_rules: list[dict] = []

    def __init__(self, rulebook_loader: RulebookLoader | None = None) -> None:
        from backend.domains.cn.document_review.rulebook_loader import RulebookLoader
        self.rulebook = rulebook_loader or RulebookLoader()

    def review(
        self, clause: ClassifiedClause, config: dict,
    ) -> list[ReviewIssue]:
        """Run type‑specific checks. Override in subclass."""
        return []

    @staticmethod
    def _make_issue(
        clause: ClassifiedClause,
        check_id: str,
        severity: str,
        title: str,
        problem_type: str,
        risk_analysis: str,
        recommendation: str,
    ) -> ReviewIssue:
        from uuid import uuid4
        from backend.schemas.review import ReviewSeverity, ReviewMethod, ReviewDepth

        sev_map = {"HIGH": ReviewSeverity.HIGH, "MEDIUM": ReviewSeverity.MEDIUM, "LOW": ReviewSeverity.LOW}
        return ReviewIssue(
            issue_id=f"SPEC-{check_id}-{uuid4().hex[:6]}",
            clause_id=clause.clause_id,
            file_id=clause.file_id,
            clause_type=clause.clause_type,
            severity=sev_map.get(severity, ReviewSeverity.MEDIUM),
            title=title,
            problem_type=problem_type,
            risk_analysis=risk_analysis,
            original_excerpt=clause.text[:240],
            recommendation=recommendation,
            position=clause.position,
            review_method=ReviewMethod.RULE,
            review_confidence=0.9,
            review_depth=ReviewDepth.STANDARD,
        )
