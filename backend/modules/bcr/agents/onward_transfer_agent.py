"""Agent 4: BCROnwardTransferAgent — judge whether onward transfer meets substantially equivalent protection.

Detects weak standards and missing safeguards beyond simple keyword checks:
- "trusted partner" / "substantially similar" → weak standard warning
- SCC / adequacy decision / equivalent protection → strong protection
- Assesses completeness of third-party list and authorization mechanism
"""

from __future__ import annotations

import re

from backend.modules.bcr.agents import BCRAgentBase


class BCROnwardTransferAgent(BCRAgentBase):
    agent_name = "bcr_onward_transfer"
    max_tokens = 400

    _WEAK_STANDARD_SIGNALS = [
        (r"trusted\s+(?:partner|third\s+part(?:y|ies))", "WEAK_TRUST_MODEL"),
        (r"substantially\s+similar\s+(?:obligations?|protection|standards?)", "VAGUE_EQUIVALENCE"),
        (r"comparable\s+(?:level\s+of\s+)?protection", "VAGUE_COMPARABLE"),
        (r"appropriate\s+safeguards?\s+(?:as\s+)?deemed\s+(?:necessary|appropriate)", "VAGUE_SAFEGUARDS"),
        (r"endeavou?r\s+to\s+(?:ensure|provide|maintain)", "WEAKENED_OBLIGATION"),
    ]

    _STRONG_PROTECTION_SIGNALS = [
        (r"standard\s+contractual\s+clauses?", "SCC"),
        (r"(?:EU\s+)?2021/914", "SCC_2021"),
        (r"adequacy\s+decision", "ADEQUACY"),
        (r"binding\s+corporate\s+rules?", "BCR"),
        (r"equivalent\s+(?:level\s+of\s+)?protection", "EQUIVALENT"),
        (r"approved\s+certification\s+mechanism", "CERTIFICATION"),
        (r"approved\s+code\s+of\s+conduct", "CODE_OF_CONDUCT"),
    ]

    def run(self, clause_text: str, third_parties: list[str] | None = None,
            scc_mentioned: bool = False, bcr_type: str = "BCR-C") -> dict:
        """Assess whether onward transfer protection meets substantially equivalent standard."""
        text_lower = clause_text.lower()

        # ── Check for weak standards ──
        weak_hits: list[dict] = []
        for pattern, wtype in self._WEAK_STANDARD_SIGNALS:
            for m in re.finditer(pattern, text_lower):
                weak_hits.append({"type": wtype, "quote": m.group(0)[:80]})

        # ── Check for strong protection ──
        strong_hits: list[dict] = []
        for pattern, stype in self._STRONG_PROTECTION_SIGNALS:
            for m in re.finditer(pattern, text_lower):
                strong_hits.append({"type": stype, "quote": m.group(0)[:80]})

        # ── Determine adequacy ──
        has_weak = len(weak_hits) > 0
        has_strong = len(strong_hits) > 0 or scc_mentioned

        protection_adequate = has_strong and not has_weak
        finding_type = ""
        risk_level = "LOW"
        missing_elements: list[str] = []

        if has_weak and not has_strong:
            finding_type = "ONWARD_TRANSFER_WEAK_STANDARD"
            risk_level = "HIGH"
            missing_elements = [
                f"Uses {len(weak_hits)} weak/vague protection standard(s): "
                f"{[h['type'] for h in weak_hits[:3]]}",
                "No reference to SCC, adequacy decision, or equivalent legal instrument found"
            ]
        elif has_weak and has_strong:
            finding_type = "ONWARD_TRANSFER_MIXED_SIGNALS"
            risk_level = "MEDIUM"
            missing_elements = [
                "Both strong and weak protection standards detected — "
                "strong protections may be undermined by vague fallback language"
            ]
        elif not has_strong and not scc_mentioned:
            finding_type = "ONWARD_TRANSFER_NO_SAFEGUARD"
            risk_level = "HIGH"
            missing_elements = [
                "No reference to any recognized transfer safeguard (SCC, adequacy, BCR, certification)"
            ]
        else:
            protection_adequate = True

        # ── Check third-party list completeness ──
        if third_parties and len(third_parties) == 0:
            missing_elements.append("Third-party/sub-processor list is empty — "
                                     "cannot verify that all onward recipients are covered")

        # ── Build recommendation ──
        recommendation = ""
        if finding_type == "ONWARD_TRANSFER_WEAK_STANDARD":
            recommendation = (
                "Replace vague protection commitments with explicit reference to "
                "EU Standard Contractual Clauses (2021/914) or equivalent legal instrument. "
                "Require that all onward transfers be subject to SCCs, adequacy decision, "
                "or approved certification mechanism."
            )
        elif finding_type == "ONWARD_TRANSFER_NO_SAFEGUARD":
            recommendation = (
                "Add explicit requirement that onward transfers must be covered by "
                "SCCs (EU 2021/914), an adequacy decision, or binding corporate rules. "
                "Include a complete list of all third-party recipients."
            )

        return {
            "finding_type": finding_type or "ONWARD_TRANSFER_ACCEPTABLE",
            "protection_adequate": protection_adequate,
            "risk_level": risk_level,
            "weak_signals_detected": len(weak_hits),
            "strong_protection_indicators": len(strong_hits),
            "missing_elements": missing_elements,
            "recommendation": recommendation or (
                "Onward transfer protections appear adequate. "
                "Ensure third-party list is kept up to date and SCC/adequacy "
                "references cover all current and future recipients."
            ),
        }
