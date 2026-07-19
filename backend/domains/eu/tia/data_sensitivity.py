"""TIA data sensitivity classifier."""

from __future__ import annotations

import json
from pathlib import Path

from backend.domains.eu.tia.schema import TIAStructuredInput


class TIADataSensitivity:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parent / "data" / "tia_country_riskbook.json"
        self.riskbook = json.loads(path.read_text(encoding="utf-8"))

    def assess(self, structured: TIAStructuredInput | None) -> dict:
        if structured is None:
            return {"sensitivity": "unknown", "max_weight": 0, "special_categories": [], "risk_factor": 1.0}

        weights = self.riskbook.get("data_sensitivity_weights", {})
        max_w = 0
        special: list[str] = []
        for cat in structured.data_categories:
            w = weights.get(cat, 2)
            if w > max_w:
                max_w = w
            if w >= 5:
                special.append(cat)

        if structured.has_special_category_data:
            max_w = max(max_w, 5)
            special = list(set(special + structured.special_category_types))

        if max_w >= 5:
            sensitivity = "very_high"
            risk_factor = 2.0
        elif max_w >= 4:
            sensitivity = "high"
            risk_factor = 1.5
        elif max_w >= 3:
            sensitivity = "medium_high"
            risk_factor = 1.25
        elif max_w >= 2:
            sensitivity = "medium"
            risk_factor = 1.0
        else:
            sensitivity = "low"
            risk_factor = 0.75

        return {
            "sensitivity": sensitivity, "max_weight": max_w,
            "special_categories": special, "risk_factor": risk_factor,
        }
