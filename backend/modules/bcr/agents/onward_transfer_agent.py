"""Agent 4: BCROnwardTransferAgent — judge substantive adequacy of transfer protections."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCROnwardTransferAgent(BCRAgentBase):
    agent_name = "bcr_onward_transfer"
    max_tokens = 400

    def run(self, clause_text: str, has_scc: bool, has_adequacy: bool,
            has_derogation: bool, bcr_type: str) -> dict:
        prompt = f"""Evaluate whether this onward transfer clause provides adequate GDPR protection.

BCR Type: {bcr_type}
Clause: {clause_text[:800]}
Already detected: SCC={has_scc}, Adequacy={has_adequacy}, Derogation={has_derogation}

Return JSON:
{{
  "protection_adequate": true | false,
  "finding_type": "ONWARD_TRANSFER_WEAK_STANDARD" | null,
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "finding": "<one sentence if not adequate, else empty>",
  "recommendation": "<one sentence if not adequate, else empty>"
}}"""
        result = self._call_llm(prompt) or {
            "protection_adequate": has_scc or has_adequacy,
            "finding_type": None, "risk_level": "LOW", "finding": "", "recommendation": "",
        }
        result.setdefault("protection_adequate", has_scc or has_adequacy)
        return result
