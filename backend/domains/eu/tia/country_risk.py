"""TIA country risk assessor."""

from __future__ import annotations

import json
from pathlib import Path

from backend.domains.eu.tia.schema import TIACountryRisk, TIAStructuredInput
from backend.domains.eu.tia.country_names import country_name_matches, normalize_country_name



class TIACountryRiskAssessor:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parent / "data" / "tia_country_riskbook.json"
        self.riskbook = json.loads(path.read_text(encoding="utf-8"))

    def assess(self, structured: TIAStructuredInput | None) -> TIACountryRisk:
        if structured is None:
            return TIACountryRisk(country="unknown", risk_level="MEDIUM")

        dest = (structured.destination_country or structured.importer_country or "").strip()
        dest = normalize_country_name(dest)
        country_risks: dict = self.riskbook.get("country_risks", {})

        # Exact match first
        for country_name, risk_info in country_risks.items():
            if dest.lower() == country_name.lower():
                return TIACountryRisk(country=country_name, **risk_info)

        # Fuzzy match
        for country_name, risk_info in country_risks.items():
            if country_name_matches(dest, country_name):
                return TIACountryRisk(country=country_name, **risk_info)

        # Unknown country
        return TIACountryRisk(
            country=dest or "unknown",
            risk_level="MEDIUM",
            risk_sources=["No structured risk data for this country"],
            notes=f"No country risk profile found for '{dest}'. Manual legal assessment required.",
        )
