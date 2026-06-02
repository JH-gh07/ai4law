"""Agent 10: BCRRemediationAgent — generate executable revision suggestions."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRRemediationAgent(BCRAgentBase):
    agent_name = "bcr_remediation"
    max_tokens = 800

    def run(self, finding_title: str, finding_text: str,
            legal_basis: list[str], bcr_type: str,
            existing_text: str = "") -> dict:
        prompt = f"""Generate an executable remediation for this BCR compliance finding.

BCR Type: {bcr_type}
Finding: {finding_title}
{finding_text[:400]}
Legal basis: {legal_basis[:3]}
Existing text (if any): {existing_text[:400]}

Return JSON:
{{
  "fix_type": "INSERT_CLAUSE" | "REPLACE_CLAUSE" | "DELETE_CLAUSE" | "ADD_CHAPTER" | "CLARIFY",
  "insert_location": "e.g. After Chapter 8 Liability",
  "suggested_text": "<draft clause text, up to 300 words>",
  "rationale": "<why this fix addresses the GDPR/EDPB requirement>",
  "key_elements": ["element1 included in draft", "element2"]
}}"""
        result = self._call_llm(prompt) or {
            "fix_type": "CLARIFY", "insert_location": "",
            "suggested_text": "Agent unavailable — please manually draft revision.",
            "rationale": "", "key_elements": [],
        }
        result.setdefault("fix_type", "CLARIFY")
        result.setdefault("suggested_text", "")
        return result
