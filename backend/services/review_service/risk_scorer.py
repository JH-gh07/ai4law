"""RiskScorer — weighted risk scoring for review issues and overall assessment."""

from __future__ import annotations

from backend.schemas.review import MissingItem, ReviewIssue, ReviewSeverity
from backend.services.review_service.rulebook_loader import RulebookLoader


class RiskScorer:
    """Calculate weighted risk scores for individual issues and overall review.

    Formula per issue:
      risk_score = clause_type_weight × severity_weight
                 + cross_border_bonus (+15)
                 + sensitive_data_bonus (+15)
                 + minor_data_bonus (+15)
                 + scc_conflict_bonus (+20)

    Then normalized to 0–100 range.
    """

    # Bonus conditions — clause types that trigger extra risk weight
    CROSS_BORDER_TYPES = {"CROSS_BORDER_TRANSFER", "ONWARD_TRANSFER", "GOVERNMENT_ACCESS"}
    SENSITIVE_DATA_TYPES = {"SENSITIVE_PI"}
    MINOR_TYPES = {"MINOR_PROTECTION"}
    SCC_CONFLICT_TYPES = {"LIABILITY"}  # liability issues in SCC context get bonus

    def __init__(self, rulebook_loader: RulebookLoader | None = None) -> None:
        self.rulebook = rulebook_loader or RulebookLoader()

    # ------------------------------------------------------------------
    # Per‑issue scoring
    # ------------------------------------------------------------------

    def score_issue(self, issue: ReviewIssue) -> float:
        """Calculate 0–100 risk score for a single issue."""
        clause_type = issue.clause_type.value

        base = (
            self.rulebook.get_risk_weight(clause_type)
            * self.rulebook.get_severity_weight(issue.severity.value)
        )

        # Bonuses
        bonus = 0
        if clause_type in self.CROSS_BORDER_TYPES:
            bonus += 15
        if clause_type in self.SENSITIVE_DATA_TYPES:
            bonus += 15
        if clause_type in self.MINOR_TYPES:
            bonus += 15
        if clause_type in self.SCC_CONFLICT_TYPES and "境外法院" in issue.title:
            bonus += 20

        # Normalize to 0–100 (max possible base: 8 * 10 = 80, max bonus: 65)
        raw = base + bonus
        return min(round(raw, 1), 100.0)

    # ------------------------------------------------------------------
    # Overall scoring
    # ------------------------------------------------------------------

    def overall_score(
        self,
        issues: list[ReviewIssue],
        missing_items: list[MissingItem] | None = None,
    ) -> float:
        """Calculate overall risk score 0–100 from all issues and missing items."""
        missing = missing_items or []

        if not issues and not missing:
            return 0.0

        # Weighted average of issue scores
        issue_scores = [self.score_issue(i) for i in issues]

        # Missing item penalty: each HIGH severity missing adds penalty
        missing_high_count = sum(1 for m in missing if m.severity == ReviewSeverity.HIGH)
        missing_med_count = sum(1 for m in missing if m.severity == ReviewSeverity.MEDIUM)
        missing_penalty = missing_high_count * 8 + missing_med_count * 4

        if issue_scores:
            avg_issue = sum(issue_scores) / len(issue_scores)
        else:
            avg_issue = 0.0

        total = avg_issue + missing_penalty
        return min(round(total, 1), 100.0)

    # ------------------------------------------------------------------
    # Rating label
    # ------------------------------------------------------------------

    def rating_label(self, overall_score: float) -> str:
        """Convert numeric score to Chinese risk rating."""
        if overall_score >= 70:
            return "高风险"
        elif overall_score >= 40:
            return "中风险"
        return "低风险"
