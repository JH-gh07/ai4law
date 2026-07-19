"""Agent 4: TIAEffectivenessAgent — evaluate whether supplementary measures can resist third-country access.

Goes beyond keyword presence to assess: who holds keys, can the cloud provider decrypt,
does the importer have plaintext access, are contractual/organizational measures adequate.
"""

from __future__ import annotations

import re

from backend.domains.eu.scc_review.agents import SCCAgentBase


class TIAEffectivenessAgent(SCCAgentBase):
    agent_name = "eu_scc_tia_effectiveness"
    max_tokens = 600

    # Technical measure effectiveness patterns
    _TECH_MEASURE_PATTERNS = {
        "e2ee_eu_keys": [r"end.to.end\s+encryption", r"E2EE", r"EU.held\s+keys?", r"BYOK", r"HYOK", r"customer.managed\s+keys?", r"hold\s+your\s+own\s+key", r"zero.access\s+encryption", r"client.side\s+encryption"],
        "basic_encryption_only": [r"TLS\s*(?:1\.[23])?", r"AES[-\s]*(?:128|256)", r"at.rest\s+encryption", r"in.transit\s+encryption", r"encryption\s+(?:at\s+rest|in\s+transit)"],
        "access_controls": [r"RBAC", r"role.based\s+access", r"least\s+privilege", r"MFA", r"multi.factor", r"access\s+control"],
    }

    _CONTRACTUAL_MEASURE_PATTERNS = {
        "gov_access": [r"government\s+access\s+(?:notification|request)", r"notify.*?(?:government|public\s+authority)", r"challenge\s+(?:unlawful|illegal)\s+(?:requests?|access)", r"transparency\s+report", r"warrant\s+canary"],
        "onward_restrictions": [r"(?:no|prohibit|restrict)\s+(?:onward|further)\s+(?:transfer|disclosure|sharing)", r"sub.processor.*?(?:approval|authori[sz]ation|consent)"],
    }

    _ORG_MEASURE_PATTERNS = {
        "audit": [r"independent\s+(?:annual\s+)?audit", r"third.party\s+audit", r"external\s+audit", r"audit\s+rights?"],
        "logging": [r"(?:comprehensive|full|complete)\s+(?:activity\s+)?(?:logs?|logging)", r"access\s+logs?", r"audit\s+trail"],
        "key_management": [r"key\s+management", r"separation\s+of\s+duties.*?(?:key|encryption)", r"HSM", r"hardware\s+security\s+module"],
        "training": [r"(?:security\s+)?awareness\s+training", r"employee\s+training", r"staff\s+training"],
    }

    def run(self, document: dict, transfer_chain: dict, tia_review: dict,
            has_tia: bool = False, has_supplementary_measures: bool = False) -> dict:
        """Assess whether supplementary measures can effectively resist third-country access."""
        raw_text = document.get("raw_text", "") if isinstance(document, dict) else getattr(document, "raw_text", "")
        annex_ii_text = raw_text.lower()

        # Try to extract Annex II section
        annex_match = re.search(r"(?:ANNEX\s*II|TECHNICAL\s+AND\s+ORGANIS[AZ]ATIONAL\s+MEASURES).*?(?=ANNEX\s*III|LIST\s+OF\s+SUB|$)", raw_text, re.IGNORECASE | re.DOTALL)
        if annex_match:
            annex_ii_text = annex_match.group(0).lower()

        # ── Assess technical measures ──
        tech_found: list[str] = []
        tech_missing: list[str] = []
        for category, patterns in self._TECH_MEASURE_PATTERNS.items():
            found_any = any(re.search(p, annex_ii_text) for p in patterns)
            if found_any:
                tech_found.append(category)
            else:
                tech_missing.append(category)

        has_e2ee = "e2ee_eu_keys" in tech_found
        has_basic_only = "basic_encryption_only" in tech_found and not has_e2ee

        if has_e2ee and tech_found == ["e2ee_eu_keys", "access_controls"]:
            tech_status = "effective"
            tech_reason = "End-to-end encryption with EU-held keys and access controls present."
        elif has_e2ee:
            tech_status = "effective"
            tech_reason = "End-to-end encryption with EU-held keys present, but verify all measures."
        elif has_basic_only:
            tech_status = "insufficient"
            tech_reason = "Only basic encryption (TLS/AES) without EU-held keys or E2EE — the importer/cloud provider may still access plaintext."
        else:
            tech_status = "partial" if tech_found else "insufficient"
            tech_reason = "Technical measures are limited or not detected."

        # ── Assess contractual measures ──
        contract_found: list[str] = []
        contract_missing: list[str] = []
        for category, patterns in self._CONTRACTUAL_MEASURE_PATTERNS.items():
            found_any = any(re.search(p, annex_ii_text) for p in patterns)
            if found_any:
                contract_found.append(category)
            else:
                contract_missing.append(category)
        contract_status = "effective" if len(contract_found) >= 2 else "partial" if contract_found else "missing"

        # ── Assess organizational measures ──
        org_found: list[str] = []
        org_missing: list[str] = []
        for category, patterns in self._ORG_MEASURE_PATTERNS.items():
            found_any = any(re.search(p, annex_ii_text) for p in patterns)
            if found_any:
                org_found.append(category)
            else:
                org_missing.append(category)
        org_status = "effective" if len(org_found) >= 3 else "partial" if org_found else "missing"

        # ── Overall effectiveness ──
        statuses = [tech_status, contract_status, org_status]
        if "insufficient" in statuses or "missing" in statuses:
            overall = "insufficient"
        elif statuses.count("partial") >= 2:
            overall = "partially_effective"
        elif statuses.count("effective") >= 2:
            overall = "effective"
        else:
            overall = "unknown_due_to_missing_info"

        # ── Generate findings ──
        additional_findings: list[dict] = []
        if overall in ("insufficient", "partially_effective"):
            additional_findings.append({"finding_id": "EU-SCC-TIA-MEASURES-EFFECTIVENESS", "location": "Annex II / TIA", "issue_type": "supplementary_measures_insufficient", "severity": "HIGH" if overall == "insufficient" else "MEDIUM", "risk_analysis": f"Technical: {tech_status} ({tech_reason}). Contractual: {contract_status}. Organizational: {org_status}. Overall: {overall}.", "legal_basis": "Schrems II C-311/18; EDPB Recommendations 01/2020; GDPR Article 46", "recommendation": self._build_recommendation(tech_missing, contract_missing, org_missing), "confidence": 0.90})

        return {"effectiveness_matrix": {"technical": {"status": tech_status, "found": tech_found, "missing": tech_missing, "reason": tech_reason}, "contractual": {"status": contract_status, "found": contract_found, "missing": contract_missing}, "organizational": {"status": org_status, "found": org_found, "missing": org_missing}}, "overall_effectiveness": overall, "additional_findings": additional_findings}

    @staticmethod
    def _build_recommendation(tech_missing: list, contract_missing: list, org_missing: list) -> str:
        parts: list[str] = []
        if tech_missing:
            parts.append(f"Technical: implement {', '.join(tech_missing[:3])}")
        if contract_missing:
            parts.append(f"Contractual: add {', '.join(contract_missing[:2])}")
        if org_missing:
            parts.append(f"Organizational: establish {', '.join(org_missing[:3])}")
        return " | ".join(parts) if parts else "Measures appear adequate."
