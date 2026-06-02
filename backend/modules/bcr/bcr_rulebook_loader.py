"""BCRRulebookLoader — validated access to bcr_rulebook.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BCRRulebookLoader:
    def __init__(self, rulebook_path: Path | None = None) -> None:
        if rulebook_path is None:
            rulebook_path = Path(__file__).resolve().parent / "data" / "bcr_rulebook.json"
        self.rulebook: dict[str, Any] = json.loads(rulebook_path.read_text(encoding="utf-8"))
        self._validate()

    def get_bcr_c_signals(self) -> list[str]:
        return list(self.rulebook.get("bcr_type_classification", {}).get("bcr_c_signals", []))

    def get_bcr_p_signals(self) -> list[str]:
        return list(self.rulebook.get("bcr_type_classification", {}).get("bcr_p_signals", []))

    def get_mismatch_rules(self) -> list[dict]:
        return list(self.rulebook.get("bcr_type_classification", {}).get("module_mismatch_rules", []))

    def get_requirements(self, bcr_type: str) -> list[dict]:
        if bcr_type == "BCR-C":
            return list(self.rulebook.get("bcr_c_requirements", []))
        elif bcr_type == "BCR-P":
            return list(self.rulebook.get("bcr_p_requirements", []))
        return []

    def get_shared_requirements(self) -> list[dict]:
        return list(self.rulebook.get("shared_requirements", []))

    def get_all_requirements(self, bcr_type: str) -> list[dict]:
        return self.get_requirements(bcr_type) + self.get_shared_requirements()

    def get_required_sections(self, bcr_type: str) -> list[str]:
        key = f"{bcr_type.lower().replace('-', '_')}_required_sections"
        return list(self.rulebook.get("document_structure_checklist", {}).get(key, []))

    def get_risk_weight(self, requirement_id: str) -> int:
        return self.rulebook.get("risk_weights", {}).get(requirement_id, 3)

    def get_severity_weight(self, severity: str) -> int:
        return self.rulebook.get("severity_weights", {}).get(severity, 2)

    def _validate(self) -> None:
        required = ["bcr_type_classification", "bcr_c_requirements", "shared_requirements",
                     "document_structure_checklist", "risk_weights", "severity_weights"]
        for key in required:
            if key not in self.rulebook:
                raise ValueError(f"Missing required section: {key}")
