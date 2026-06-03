"""TIA route decider — determines whether full TIA is needed."""

from __future__ import annotations

import json
from pathlib import Path

from backend.modules.tia.schema import TIARouteDecision, TIAStructuredInput


class TIARouteDecider:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parent / "data" / "tia_country_riskbook.json"
        self.riskbook = json.loads(path.read_text(encoding="utf-8"))

    def decide(self, transfer_tool: str, structured: TIAStructuredInput | None) -> TIARouteDecision:
        dest = (structured.destination_country or structured.importer_country or "").strip()
        tool = transfer_tool.lower()

        # 1. Check adequacy
        adequacy_map: dict = self.riskbook.get("adequacy_countries", {})
        for country_name, info in adequacy_map.items():
            if country_name.lower() in dest.lower() or dest.lower() in country_name.lower():
                return TIARouteDecision(
                    route="adequacy_simplified",
                    need_full_tia=False,
                    adequacy_decision_exists=True,
                    adequacy_country=country_name,
                    adequacy_notes=[info.get("source", ""), info.get("notes", "")],
                    reason=f"Destination country ({country_name}) has an EU adequacy decision. No full TIA required.",
                )

        # 2. SCC route
        if tool == "scc":
            return TIARouteDecision(
                route="full_tia_scc", need_full_tia=True,
                reason="SCC transfer to non-adequacy country — full TIA with supplementary measures assessment required.",
            )

        # 3. BCR route
        if tool == "bcr":
            return TIARouteDecision(
                route="full_tia_bcr", need_full_tia=True,
                reason="BCR transfer to non-adequacy country — full TIA required.",
            )

        # 4. Derogation
        if tool == "derogation":
            return TIARouteDecision(
                route="derogation_exception", need_full_tia=True,
                reason="Article 49 derogation — assess strict necessity, occasional nature, and explicit consent.",
            )

        # 5. Unknown
        return TIARouteDecision(
            route="missing_or_invalid_tool", need_full_tia=False,
            reason="No valid transfer tool identified. User must specify an Article 46 or 49 mechanism.",
        )
