"""Agent 5: BCRTiaReasoningAgent — assess TIA completeness as a process, not a keyword."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRTiaReasoningAgent(BCRAgentBase):
    agent_name = "bcr_tia_reasoning"
    max_tokens = 500

    def run(self, tia_section: str, gov_access_section: str, legal_refs: list[str]) -> dict:
        prompt = f"""Assess whether the TIA section forms a complete, executable assessment mechanism.

TIA section:
{tia_section[:1500]}

Government access section:
{gov_access_section[:800]}

Legal references: {legal_refs[:5]}

Return JSON:
{{
  "tia_completeness": "complete" | "partial" | "incomplete",
  "missing_elements": ["element1", "element2"],
  "has_edpb_method": true | false,
  "has_periodic_review": true | false,
  "has_supplementary_measures": true | false,
  "has_suspension_mechanism": true | false,
  "has_gov_access_procedure": true | false,
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "finding_summary": "<one sentence>",
  "recommendation": "<one sentence>"
}}"""
        result = self._call_llm(prompt) or {
            "tia_completeness": "incomplete", "missing_elements": ["Unable to verify via agent"],
            "has_edpb_method": False, "has_periodic_review": False,
            "has_supplementary_measures": False, "has_suspension_mechanism": False,
            "has_gov_access_procedure": False, "risk_level": "MEDIUM",
            "finding_summary": "Agent unavailable — TIA assessment limited to keyword checks.",
            "recommendation": "Manual review of TIA completeness recommended.",
        }
        result.setdefault("tia_completeness", "incomplete")
        result.setdefault("missing_elements", [])
        return result
