"""TIA country risk assessor."""

from __future__ import annotations

import json
from pathlib import Path

from backend.domains.eu.tia.schema import TIACountryRisk, TIAStructuredInput


COUNTRY_ALIASES = {
    "us": "United States",
    "u.s.": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
}


class TIACountryRiskAssessor:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parent / "data" / "tia_country_riskbook.json"
        self.riskbook = json.loads(path.read_text(encoding="utf-8"))

    def assess(self, structured: TIAStructuredInput | None) -> TIACountryRisk:
        if structured is None:
            return TIACountryRisk(country="unknown", risk_level="MEDIUM")

        dest = (structured.destination_country or structured.importer_country or "").strip()
        dest = COUNTRY_ALIASES.get(dest.lower(), dest)
        country_risks: dict = self.riskbook.get("country_risks", {})

        # Exact match first
        for country_name, risk_info in country_risks.items():
            if dest.lower() == country_name.lower():
                return TIACountryRisk(country=country_name, **risk_info)

        # Fuzzy match
        for country_name, risk_info in country_risks.items():
            if country_name.lower() in dest.lower() or dest.lower() in country_name.lower():
                return TIACountryRisk(country=country_name, **risk_info)

        # Unknown country
        return TIACountryRisk(
            country=dest or "unknown",
            risk_level="MEDIUM",
            risk_sources=["No structured risk data for this country"],
            notes=f"No country risk profile found for '{dest}'. Manual legal assessment required.",
        )
