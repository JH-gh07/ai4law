"""Agent 8: BCRLegalGroundingAgent — validate that citations actually support findings."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRLegalGroundingAgent(BCRAgentBase):
    agent_name = "bcr_legal_grounding"
    max_tokens = 500

    def run(self, finding_title: str, finding_text: str,
            citations: list[dict], requirement_id: str) -> dict:
        cite_list = "\n".join(
            f"- [{i}] {c.get('source','?')}: {c.get('snippet','')[:120]}"
            for i, c in enumerate(citations[:5])
        )
        prompt = f"""Classify each citation's relevance to this finding.

Finding: {finding_title}
{finding_text[:300]}
Requirement: {requirement_id}

Citations:
{cite_list}

Return JSON:
{{
  "primary_basis": [
    {{"source": "GDPR", "article": "Art 47(1)(b)", "used_for": "proves mandatory requirement"}}
  ],
  "supporting_basis": [
    {{"source": "...", "used_for": "..."}}
  ],
  "discarded_basis": [
    {{"source": "...", "reason": "not relevant because ..."}}
  ],
  "grounding_adequate": true | false
}}"""
        result = self._call_llm(prompt) or {
            "primary_basis": [], "supporting_basis": [],
            "discarded_basis": [], "grounding_adequate": bool(citations),
        }
        result.setdefault("grounding_adequate", bool(citations))
        return result
