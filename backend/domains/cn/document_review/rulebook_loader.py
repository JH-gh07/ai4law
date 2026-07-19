"""RulebookLoader — validated access to the enhanced review_rulebook.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from backend.core.resource_paths import rule_resource_path


class RulebookLoader:
    """Load and provide typed access to the review rulebook.

    Caches compiled regex patterns from DSL checks for repeated use.
    """

    def __init__(self, rulebook_path: Path | None = None) -> None:
        if rulebook_path is None:
            rulebook_path = rule_resource_path("cn", "review_rulebook.json")
        self._path = rulebook_path
        self.rulebook: dict[str, Any] = json.loads(rulebook_path.read_text(encoding="utf-8"))
        self._compiled: dict[str, re.Pattern] = {}
        self._validate()

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_clause_config(self, clause_type: str) -> dict:
        """Return full configuration for a single clause type, or empty dict."""
        return dict(self.rulebook.get("clause_types", {}).get(clause_type, {}))

    def get_all_clause_types(self) -> list[str]:
        """Return all known clause type keys (excluding OTHER)."""
        return list(self.rulebook.get("clause_types", {}).keys())

    def get_clause_display_name(self, clause_type: str) -> str:
        return self.get_clause_config(clause_type).get("display_name", clause_type)

    def get_keywords(self, clause_type: str) -> list[str]:
        return list(self.get_clause_config(clause_type).get("keywords", []))


    def get_citations(self, clause_type: str) -> list[dict]:
        """Return citations as list of {source, article, snippet} dicts."""
        return list(self.get_clause_config(clause_type).get("citations", []))

    def get_citation_strings(self, clause_type: str) -> list[str]:
        """Return citations as formatted strings like '《个保法》第13条'."""
        return [
            f"《{c.get('source', '')}》{c.get('article', '')}".strip("》").strip()
            for c in self.get_citations(clause_type)
        ]

    def get_dsl_checks(self, clause_type: str) -> list[dict]:
        return list(self.get_clause_config(clause_type).get("dsl_checks", []))

    def get_checklist(self, document_type: str) -> dict:
        """Return checklist config for a document type."""
        return dict(
            self.rulebook.get("document_type_checklists", {}).get(document_type, {})
        )




    def get_risk_weight(self, clause_type: str) -> int:
        return self.rulebook.get("risk_weights", {}).get(clause_type, 2)

    def get_severity_weight(self, severity: str) -> int:
        return self.rulebook.get("severity_weights", {}).get(severity, 2)

    def get_high_priority_types(self) -> list[str]:
        return list(self.rulebook.get("HIGH_PRIORITY_TYPES", []))

    def get_medium_priority_types(self) -> list[str]:
        return list(self.rulebook.get("MEDIUM_PRIORITY_TYPES", []))


    def get_multi_label_keywords(self, clause_type: str) -> dict[str, list[str]]:
        return dict(self.get_clause_config(clause_type).get("multi_label_keywords", {}))


    def get_checklist_requirement(self, clause_type: str) -> dict:
        return dict(self.get_clause_config(clause_type).get("checklist_requirement", {}))

    # ------------------------------------------------------------------
    # Compiled pattern access (for DSL checks)
    # ------------------------------------------------------------------

    def get_compiled_pattern(self, check_id: str, pattern: str) -> re.Pattern:
        """Return a compiled regex pattern, cached by check_id."""
        key = f"{check_id}:{pattern}"
        if key not in self._compiled:
            self._compiled[key] = re.compile(pattern)
        return self._compiled[key]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Validate rulebook structure and cross-references."""
        clause_types = self.rulebook.get("clause_types", {})
        if not clause_types:
            raise ValueError("Rulebook contains no clause_types")

        required_sections = [
            "clause_types", "document_type_checklists",
            "risk_weights", "severity_weights",
            "HIGH_PRIORITY_TYPES", "MEDIUM_PRIORITY_TYPES",
        ]
        for section in required_sections:
            if section not in self.rulebook:
                raise ValueError(f"Rulebook missing required section: {section}")

        # Validate clause type cross-references
        all_types = set(clause_types.keys())
        for ct_name in self.get_high_priority_types():
            if ct_name not in all_types:
                raise ValueError(f"HIGH_PRIORITY_TYPES references unknown type: {ct_name}")
        for ct_name in self.get_medium_priority_types():
            if ct_name not in all_types:
                raise ValueError(f"MEDIUM_PRIORITY_TYPES references unknown type: {ct_name}")

        # Validate checklists
        for doc_type, checklist in self.rulebook.get("document_type_checklists", {}).items():
            for req_type in checklist.get("required_clause_types", []):
                if req_type not in all_types:
                    raise ValueError(f"Checklist {doc_type} refs unknown type: {req_type}")
            for rec_type in checklist.get("recommended_clause_types", []):
                if rec_type not in all_types:
                    raise ValueError(f"Checklist {doc_type} refs unknown type: {rec_type}")

        # Validate risk_weights coverage
        for ct_name in all_types:
            if ct_name not in self.rulebook.get("risk_weights", {}):
                raise ValueError(f"clause_type {ct_name} missing from risk_weights")

        # Pre-compile DSL patterns to catch regex errors early
        for ct_name, config in clause_types.items():
            for check in config.get("dsl_checks", []):
                pattern = check.get("pattern", "")
                if pattern:
                    try:
                        self.get_compiled_pattern(check["id"], pattern)
                    except re.error as exc:
                        raise ValueError(
                            f"Invalid regex in {ct_name}.{check['id']}: {pattern}"
                        ) from exc
