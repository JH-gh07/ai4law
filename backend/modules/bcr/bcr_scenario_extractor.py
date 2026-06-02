"""BCRScenarioExtractor — extract controller/processor role, member countries, etc."""

from __future__ import annotations

import re

from backend.modules.bcr.bcr_document_parser import BCRStructuredDocument
from backend.modules.bcr.schema import BCRScenarioContext


class BCRScenarioExtractor:
    def extract(self, text: str, doc: BCRStructuredDocument | None = None,
                user_context: BCRScenarioContext | None = None) -> BCRScenarioContext:
        base = user_context or BCRScenarioContext()
        t = text[:8000]

        if not base.company_name:
            m = re.search(
                r"(?:Company|Corporation|Group|Entity|Inc\.?|Ltd\.?|LLC|GmbH|S\.A\.|N\.V\.)"
                r"\s*[:\.]?\s*([A-Z][A-Za-z\s&\.]{3,60})",
                t[:2000],
            )
            if m: base.company_name = m.group(1).strip()

        if not base.eu_liable_entity:
            m = re.search(
                r"(?:EU|European|established in|located in)\s"
                r"(?:entity|member|company|subsidiary)[\s:]+([A-Za-z\s&\.]{3,60})",
                t, re.IGNORECASE,
            )
            if m: base.eu_liable_entity = m.group(1).strip()

        if base.processes_on_behalf_of_clients is None:
            base.processes_on_behalf_of_clients = bool(re.search(
                r"(?:on behalf of clients|on behalf of.*controller|"
                r"process.*personal data.*for.*client|"
                r"as a processor.*for|acting as.*processor|"
                r"according to.*controller.*instructions)",
                t, re.IGNORECASE,
            ))

        countries: list[str] = []
        for cc in ["Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech",
                     "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
                     "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
                     "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia",
                     "Slovenia", "Spain", "Sweden", "United Kingdom", "Switzerland",
                     "Norway", "Iceland", "Liechtenstein",
                     "United States", "India", "China", "Japan", "Singapore",
                     "Australia", "Brazil", "Canada", "Mexico", "South Africa",
                     "South Korea", "Hong Kong", "Taiwan", "Malaysia", "Thailand",
                     "Vietnam", "Indonesia", "Philippines", "Turkey", "Russia",
                     "UAE", "Saudi Arabia", "Israel", "Argentina", "Chile", "Colombia"]:
            if re.search(rf"\b{re.escape(cc)}\b", t):
                countries.append(cc)
        existing = set(base.third_countries)
        for c in countries:
            if c not in existing:
                base.third_countries.append(c)

        base.auto_extracted_facts = {
            k: str(v) for k, v in {
                "has_eu_entity": bool(base.eu_liable_entity),
                "processes_for_clients": base.processes_on_behalf_of_clients,
                "third_country_count": str(len(base.third_countries)),
                "document_title": doc.title if doc else "",
            }.items() if v
        }

        return base
