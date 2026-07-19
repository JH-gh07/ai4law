"""Agent 1: DocumentStructureAgent — complete parsed fields, flag uncertain items.

Patches SCCDocument parsed by regex to fix missing fields, misidentified roles,
unparsed annex content, and cross-reference gaps. Does NOT make legal judgments.
"""

from __future__ import annotations

import re

from backend.domains.eu.scc_review.agents import SCCAgentBase


class DocumentStructureAgent(SCCAgentBase):
    agent_name = "eu_scc_document_structure"
    max_tokens = 800

    # Known cloud provider / sub-processor names
    _CLOUD_PATTERNS = [
        r"(?:AWS|Amazon\s+Web\s+Services?)",
        r"(?:Azure|Microsoft\s+Azure)",
        r"(?:GCP|Google\s+Cloud\s+Platform)",
        r"(?:Salesforce|SFDC)",
        r"(?:Snowflake|Databricks)",
    ]

    # Role detection patterns
    _ROLE_PATTERNS = {
        "controller": [r"(?:data\s+)?controller", r"determines?\s+(?:the\s+)?purposes?", r"as\s+(?:a\s+)?controller"],
        "processor": [r"(?:data\s+)?processor", r"on\s+behalf\s+of", r"according\s+to\s+instructions"],
    }

    def run(self, raw_text: str, parsed_document: dict,
            declared_module: str = "", parser_warnings: list[str] | None = None) -> dict:
        """Check parsed document completeness, re-scan raw text for missing fields,
        and produce patches with source quotes and confidence scores.
        """
        patches: list[dict] = []
        uncertainties: list[dict] = []
        text_lower = raw_text.lower()

        # ── Step 1: Check completeness ──
        clauses = parsed_document.get("clauses", []) if isinstance(parsed_document, dict) else getattr(parsed_document, "clauses", [])
        annex_ia = parsed_document.get("annex_i_a", {}) if isinstance(parsed_document, dict) else getattr(parsed_document, "annex_i_a", None)
        annex_ib = parsed_document.get("annex_i_b", {}) if isinstance(parsed_document, dict) else getattr(parsed_document, "annex_i_b", None)
        annex_ii = parsed_document.get("annex_ii", {}) if isinstance(parsed_document, dict) else getattr(parsed_document, "annex_ii", None)
        annex_iii = parsed_document.get("annex_iii", {}) if isinstance(parsed_document, dict) else getattr(parsed_document, "annex_iii", None)

        if len(clauses) < 5:
            patches.append({"field_path": "clauses", "problem": f"Only {len(clauses)} clauses extracted", "action": "re_scan"})

        # ── Step 2: Re-locate key regions in raw text ──
        region_markers = {
            "ANNEX I.A": [r"(?:ANNEX\s*I[.\s]*A|A[.\s]*LIST\s+OF\s+PARTIES)", "parties"],
            "ANNEX I.B": [r"(?:ANNEX\s*I[.\s]*B|B[.\s]*DESCRIPTION\s+OF\s+(?:THE\s+)?TRANSFER)", "transfer_desc"],
            "ANNEX II": [r"(?:ANNEX\s*II|TECHNICAL\s+AND\s+ORGANIS[AZ]ATIONAL\s+MEASURES)", "toms"],
            "ANNEX III": [r"(?:ANNEX\s*III|LIST\s+OF\s+SUB[-\s]?PROCESSORS)", "sub_processors"],
        }
        found_regions = {}
        for region, patterns in region_markers.items():
            for pat in patterns:
                m = re.search(pat, raw_text, re.IGNORECASE)
                if m:
                    found_regions[region] = (m.start(), m.group(0))
                    break

        # ── Step 3: Detect exporters/importers ──
        exporter_match = re.search(r"(?:Data\s+)?[Ee]xporter\s*[:\-]?\s*([^\n]{5,200})", raw_text)
        importer_match = re.search(r"(?:Data\s+)?[Ii]mporter\s*[:\-]?\s*([^\n]{5,200})", raw_text)
        if exporter_match and not any(p.get("field_path") == "annex_ia.exporter" for p in patches):
            patches.append({"field_path": "annex_ia.exporter", "old_value": "", "new_value": exporter_match.group(1).strip()[:200], "source_quote": exporter_match.group(0)[:100], "confidence": 0.85})
        if importer_match and not any(p.get("field_path") == "annex_ia.importer" for p in patches):
            patches.append({"field_path": "annex_ia.importer", "old_value": "", "new_value": importer_match.group(1).strip()[:200], "source_quote": importer_match.group(0)[:100], "confidence": 0.85})

        # ── Step 4: Detect roles (controller/processor) — only fill if missing ──
        has_exporter_role = any(p.get("field_path") == "annex_ia.exporter" for p in patches)
        has_importer_role = any(p.get("field_path") == "annex_ia.importer" for p in patches)
        for role, patterns in self._ROLE_PATTERNS.items():
            for pat in patterns:
                for m in re.finditer(pat, text_lower):
                    ctx_start = max(0, m.start() - 50)
                    ctx_end = min(len(raw_text), m.end() + 80)
                    ctx = raw_text[ctx_start:ctx_end].strip()
                    if "exporter" in ctx.lower() and not has_exporter_role:
                        patches.append({"field_path": "exporter_role", "old_value": "", "new_value": role, "source_quote": ctx[:200], "confidence": 0.88})
                        has_exporter_role = True
                    elif "importer" in ctx.lower() and not has_importer_role:
                        patches.append({"field_path": "importer_role", "old_value": "", "new_value": role, "source_quote": ctx[:200], "confidence": 0.88})
                        has_importer_role = True

        # ── Step 5: Detect cloud providers / hidden sub-processors ──
        for pat in self._CLOUD_PATTERNS:
            for m in re.finditer(pat, raw_text, re.IGNORECASE):
                ctx = raw_text[max(0, m.start()-80):min(len(raw_text), m.end()+80)]
                patches.append({"field_path": "annex_iii.sub_processors", "old_value": "", "new_value": m.group(0), "source_quote": ctx[:200], "confidence": 0.82, "note": "Cloud provider detected — verify if listed in Annex III"})

        # ── Step 6: Check for "See MSA" / incomplete references ──
        for m in re.finditer(r"(?:see|refer\s+to)\s+(?:the\s+)?(?:MSA|Master\s+Service\s+Agreement|DPA|Data\s+Processing\s+Agreement)", text_lower):
            uncertainties.append({"field_path": "annex_ia", "problem": "Party information references external MSA/DPA rather than inline", "needs_human_review": True, "quote": raw_text[max(0, m.start()-20):m.end()+40]})

        return {"patches": patches, "uncertainties": uncertainties, "patch_count": len(patches), "regions_found": list(found_regions.keys()), "completeness": "ok" if len(patches) < 5 else "needs_review"}
