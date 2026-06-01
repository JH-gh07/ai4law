"""MissingItemChecker — detect globally missing clause types in documents."""

from __future__ import annotations

from uuid import uuid4

from backend.schemas.review import ClauseType, ClassifiedClause, MissingItem, ReviewSeverity
from backend.services.review_service.rulebook_loader import RulebookLoader


class MissingItemChecker:
    """Check document for entirely missing required clause types.

    Compares classified clauses against the document type checklist from
    the rulebook, generating MissingItem for each absent required type.
    """

    def __init__(self, rulebook_loader: RulebookLoader | None = None) -> None:
        self.rulebook = rulebook_loader or RulebookLoader()

    def check(
        self,
        classified_clauses: list[ClassifiedClause],
        document_type: str,
    ) -> list[MissingItem]:
        """Check completeness and return missing items.

        A clause type is considered "present" if at least one clause is
        classified as that type (primary) with confidence ≥ 0.3.
        """
        checklist = self.rulebook.get_checklist(document_type)
        if not checklist:
            return []

        required = checklist.get("required_clause_types", [])
        recommended = checklist.get("recommended_clause_types", [])

        # Build set of covered types (primary + secondary, with threshold)
        covered_primary: set[str] = set()
        covered_secondary: set[str] = set()
        for cc in classified_clauses:
            if cc.type_confidence >= 0.3:
                covered_primary.add(cc.clause_type.value)
            for st in cc.secondary_types:
                if cc.type_confidence >= 0.3:
                    covered_secondary.add(st.value)

        missing: list[MissingItem] = []

        # Required types
        for ct_name in required:
            if ct_name in covered_primary:
                continue
            # If only in secondary types, treat as "weakly covered" → MEDIUM
            if ct_name in covered_secondary:
                missing.append(self._build_missing(
                    ct_name, ReviewSeverity.MEDIUM,
                    "在次要分类中被部分覆盖，建议补充完整条款",
                ))
                continue

            # Completely missing → HIGH
            severity_str = self._get_missing_severity(ct_name)
            severity = ReviewSeverity(severity_str) if severity_str else ReviewSeverity.HIGH
            missing.append(self._build_missing(
                ct_name, severity,
                f"文档中未找到{self.rulebook.get_clause_display_name(ct_name)}相关内容",
            ))

        # Recommended types (lower severity)
        for ct_name in recommended:
            if ct_name in covered_primary or ct_name in covered_secondary:
                continue
            missing.append(self._build_missing(
                ct_name, ReviewSeverity.LOW,
                f"建议补充{self.rulebook.get_clause_display_name(ct_name)}相关条款",
            ))

        return missing

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_missing(
        self, ct_name: str, severity: ReviewSeverity, description: str,
    ) -> MissingItem:
        config = self.rulebook.get_clause_config(ct_name)
        display = config.get("display_name", ct_name)
        citations = self.rulebook.get_citation_strings(ct_name)

        return MissingItem(
            item_id=f"MISSING-{ct_name}-{uuid4().hex[:6]}",
            clause_type=ClauseType(ct_name),
            title=f"缺少{display}条款/说明",
            description=description,
            severity=severity,
            legal_basis=citations[:3],
            recommendation=self._default_recommendation(ct_name, display),
        )

    def _get_missing_severity(self, ct_name: str) -> str | None:
        """Get the configured missing severity for this clause type."""
        req = self.rulebook.get_checklist_requirement(ct_name)
        return req.get("missing_severity")

    @staticmethod
    def _default_recommendation(ct_name: str, display_name: str) -> str:
        """Generate a default recommendation for a missing clause type."""
        return f"建议在文档中新增{display_name}相关条款，明确具体内容并确保符合《个人信息保护法》等相关法规要求。"
