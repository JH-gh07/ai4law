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
        scenario: dict | None = None,
    ) -> list[MissingItem]:
        """Check completeness and return missing items.

        A clause type is considered "present" if at least one clause is
        classified as that type (primary) with confidence ≥ 0.3.

        Supports scenario‑driven conditional requirements: when scenario
        conditions are met (e.g. has_cross_border), additional clause types
        become required beyond the static checklist.
        """
        checklist = self.rulebook.get_checklist(document_type)
        if not checklist:
            return []

        # ── Static requirements ──
        required = list(checklist.get("required_clause_types", []))
        recommended = list(checklist.get("recommended_clause_types", []))

        # ── Conditional requirements (scenario‑driven) ──
        scenario = scenario or {}
        conditional_rules = self.rulebook.rulebook.get("conditional_required", {}).get("rules", [])
        for rule in conditional_rules:
            field = rule.get("condition_field", "")
            value = rule.get("condition_value")
            actual = scenario.get(field)
            if actual is None:
                # Auto‑detect from scenario indicators
                actual = self._infer_condition(field, scenario)

            if actual == value:
                for ct in rule.get("required_types", []):
                    if ct not in required:
                        required.append(ct)

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
            # If only in secondary types → MEDIUM
            if ct_name in covered_secondary:
                missing.append(self._build_missing(
                    ct_name, ReviewSeverity.MEDIUM,
                    "在次要分类中被部分覆盖，建议补充完整条款",
                ))
                continue

            # Completely missing → configured severity or HIGH
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
            if ct_name in required:
                continue  # already flagged as required missing
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
    def _infer_condition(field: str, scenario: dict) -> bool | None:
        """Infer a scenario condition from available data when not explicitly set."""
        if field == "has_cross_border":
            indicators = scenario.get("cross_border_indicators", [])
            if indicators and len(indicators) > 0:
                return True
            facts = scenario.get("auto_extracted_facts", {})
            if facts.get("cross_border_indicator"):
                return True
        if field == "has_sensitive_pi":
            facts = scenario.get("auto_extracted_facts", {})
            if facts.get("sensitive_data_types"):
                return True
        if field == "has_minor_data":
            facts = scenario.get("auto_extracted_facts", {})
            if "未成年人" in str(facts.get("data_categories", "")):
                return True
        if field == "has_third_party_sharing":
            facts = scenario.get("auto_extracted_facts", {})
            if "第三方" in str(facts.get("data_categories", "")):
                return True
        if field == "has_entrusted_processing":
            if "委托" in str(scenario.get("transfer_purpose", "")):
                return True
        return None

    @staticmethod
    def _default_recommendation(ct_name: str, display_name: str) -> str:
        """Generate a default recommendation for a missing clause type."""
        return f"建议在文档中新增{display_name}相关条款，明确具体内容并确保符合《个人信息保护法》等相关法规要求。"
