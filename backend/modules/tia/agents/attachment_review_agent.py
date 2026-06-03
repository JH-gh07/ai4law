"""Agent 2: AttachmentReviewAgent — deep evidence review beyond keyword matching."""

from __future__ import annotations

from backend.modules.tia.agents import TIAAgentBase


class AttachmentReviewAgent(TIAAgentBase):
    """Reviews attachment evidence for substantive compliance, not just keyword presence.

    Evaluates:
    - Whether claimed encryption is truly pre-transfer + EU-controlled
    - Whether SCC clauses are complete (module, gov access, onward transfer)
    - Whether country law analysis is structured per EDPB methodology
    - Whether technical controls form a coherent defense-in-depth posture
    """
    agent_name = "tia_attachment_review"
    max_tokens = 700

    def run(self, transfer_agreement_evidence: dict | None,
            country_law_evidence: dict | None,
            technical_control_evidence: dict | None,
            structured_input_summary: dict | None) -> dict:
        ta_block = self._format_evidence(transfer_agreement_evidence, "Transfer Agreement")
        cl_block = self._format_evidence(country_law_evidence, "Country Law Analysis")
        tc_block = self._format_evidence(technical_control_evidence, "Technical Controls")
        si_block = str(structured_input_summary or {})[:500]

        prompt = f"""Review TIA attachment evidence for substantive adequacy.

User claims: {si_block}

{ta_block}

{cl_block}

{tc_block}

Return JSON:
{{
  "evidence_items": [
    {{"source": "file_role", "claim": "what is claimed", "confidence": "high|medium|low",
      "problem": "specific gap if any", "recommendation": "how to fix"}}
  ],
  "missing_evidence": ["critical item not found in any attachment"],
  "conflicts": ["contradiction between user claims and attachment evidence"],
  "overall_evidence_quality": "strong|adequate|weak|critical_gaps",
  "summary": "<one sentence overall>"
}}"""
        fallback = {
            "evidence_items": [], "missing_evidence": [],
            "conflicts": [], "overall_evidence_quality": "adequate",
            "summary": "Agent unavailable — evidence review based on keyword extraction only.",
        }
        return self._call_llm(prompt) or fallback

    @staticmethod
    def _format_evidence(ev: dict | None, label: str) -> str:
        if not ev:
            return f"{label}: No evidence extracted."
        lines = [f"{label}:"]
        for k, v in ev.items():
            if k == "role":
                continue
            lines.append(f"  - {k}: {v}")
        return "\n".join(lines[:15])
