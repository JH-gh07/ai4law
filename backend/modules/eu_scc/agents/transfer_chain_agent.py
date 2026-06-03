"""Agent 2: TransferChainAgent — infers complete data flow including hidden processors.

Builds a graph of data flow nodes and edges from document text, Annexes, and
attachment notes. Detects onward transfers to non-adequate countries, hidden
cloud providers, remote access paths, and role contradictions.
"""

from __future__ import annotations

import re

from backend.modules.eu_scc.agents import SCCAgentBase


class TransferChainAgent(SCCAgentBase):
    agent_name = "eu_scc_transfer_chain"
    max_tokens = 600

    _ADEQUACY_MAP = {  # Partial adequacy map for quick reference
        "united kingdom": True, "uk": True, "japan": True, "south korea": True, "switzerland": True,
        "canada": True, "argentina": True, "israel": True, "new zealand": True, "uruguay": True,
        "andorra": True, "faroe islands": True, "guernsey": True, "jersey": True, "isle of man": True,
        "united states": False, "usa": False, "india": False, "serbia": False,
        "china": False, "russia": False, "brazil": False, "singapore": False, "australia": False,
    }

    _CLOUD_PROVIDERS = {"AWS": "Amazon Web Services", "Azure": "Microsoft Azure", "GCP": "Google Cloud Platform",
                         "Salesforce": "Salesforce", "Snowflake": "Snowflake", "Databricks": "Databricks",
                         "Oracle Cloud": "Oracle Cloud"}

    # Patterns for detecting hidden storage/access locations
    _LOCATION_PATTERNS = [
        r"(?:stored|hosted|processed|maintained|kept)\s+(?:in|at|on)\s+([^.,;]{3,60})",
        r"(?:accessed|supported|maintained)\s+(?:from|by)\s+([^.,;]{3,60})",
        r"(?:data\s+cent(?:er|re)s?|infrastructure)\s+(?:in|at)\s+([^.,;]{3,60})",
        r"(?:sub[-\s]?process(?:or|ing))\s+(?:in|at|by)\s+([^.,;]{3,60})",
        r"(?:affiliate(?:s|d)\s+(?:in|at)\s+([^.,;]{3,60}))",
        r"(?:support\s+(?:from|team\s+in))\s+([^.,;]{3,60})",
    ]

    def run(self, document: dict, initial_chain: dict,
            uploaded_attachment_notes: list[str] | None = None) -> dict:
        """Infer complete data flow graph from document and initial chain."""
        nodes: list[dict] = []
        edges: list[dict] = []
        risk_hints: list[dict] = []
        attachments_text = " ".join(uploaded_attachment_notes or [])
        full_text = (document.get("raw_text", "") if isinstance(document, dict) else getattr(document, "raw_text", "")) + " " + attachments_text

        # ── Step 1: Extract exporter/importer from Annex I.A ──
        if isinstance(document, dict):
            parties = document.get("annex_i_a", {}).get("parties", []) if isinstance(document.get("annex_i_a"), dict) else []
        else:
            parties = getattr(getattr(document, "annex_i_a", None), "parties", [])

        exporter_found = False
        importer_found = False
        for i, party in enumerate(parties):
            party_dict = party if isinstance(party, dict) else getattr(party, "model_dump", lambda: {})()
            name = party_dict.get("name", "") or getattr(party, "name", "")
            role = party_dict.get("role", "") or getattr(party, "role", "")
            if not name:
                continue
            node_role = "controller" if "control" in role.lower() else "processor" if "process" in role.lower() else "unknown"
            nodes.append({"id": name, "role": node_role, "country": party_dict.get("country", ""), "source": f"Annex I.A party[{i}]"})
            if i == 0 and not exporter_found:
                edges.append({"from": name, "to": "", "type": "export", "basis": "Annex I.A (exporter)"})
                exporter_found = True
            elif not importer_found:
                prev_node = nodes[i-1]["id"] if i > 0 else ""
                edges.append({"from": prev_node, "to": name, "type": "transfer", "basis": "Annex I.A (importer)"})
                importer_found = True

        # ── Step 2: Scan for cloud providers ──
        for short_name, full_name in self._CLOUD_PROVIDERS.items():
            if short_name.lower() in full_text.lower() or full_name.lower() in full_text.lower():
                nodes.append({"id": full_name, "role": "cloud_provider", "type": "infrastructure", "source": "text_scan"})
                # Determine country — AWS/GCP/Azure are US
                country = "United States"  # Default for major clouds
                for m in re.finditer(rf"{re.escape(short_name)}[^.]*?(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", full_text):
                    country = m.group(1)
                nodes[-1]["country"] = country
                if not self._is_adequate(country):
                    risk_hints.append({"type": "onward_transfer_to_non_adequate_country", "country": country, "provider": full_name, "basis": "Cloud provider storage/processing", "confidence": 0.91 if country == "United States" else 0.80})

        # ── Step 3: Detect hidden locations ──
        found_countries: set[str] = set()
        for pattern in self._LOCATION_PATTERNS:
            for m in re.finditer(pattern, full_text, re.IGNORECASE):
                location = m.group(1).strip()
                if len(location) > 3 and len(location) < 80:
                    found_countries.add(location)

        for loc in found_countries:
            loc_lower = loc.lower()
            for country, adequate in self._ADEQUACY_MAP.items():
                if country in loc_lower:
                    if not adequate:
                        risk_hints.append({"type": "potential_onward_transfer", "location": loc, "adequate": False, "basis": "Location mention in document", "confidence": 0.75})

        # ── Step 4: Check for role contradictions ──
        if isinstance(initial_chain, dict):
            exp_role = initial_chain.get("exporter_role", "")
            imp_role = initial_chain.get("importer_role", "")
        else:
            exp_role = getattr(initial_chain, "exporter_role", "")
            imp_role = getattr(initial_chain, "importer_role", "")
        if exp_role == imp_role and exp_role in ("controller", "processor"):
            risk_hints.append({"type": "role_warning", "detail": f"Both exporter and importer are {exp_role} — verify module selection", "confidence": 0.70})

        return {"patched_chain": initial_chain, "chain_graph": {"nodes": nodes, "edges": edges}, "risk_hints": risk_hints, "nodes_found": len(nodes), "edges_found": len(edges)}

    def _is_adequate(self, country: str) -> bool:
        return self._ADEQUACY_MAP.get(country.lower(), False)
