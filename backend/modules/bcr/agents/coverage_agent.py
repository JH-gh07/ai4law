"""Agent 2: BCRRequirementCoverageAgent — judge substantive compliance beyond keywords."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRRequirementCoverageAgent(BCRAgentBase):
    agent_name = "bcr_requirement_coverage"
    max_tokens = 500

    def run(self, requirement_id: str, requirement_title: str,
            matched_clauses: list[str], coverage_status: str,
            legal_basis: list[str], bcr_type: str) -> dict:
        """Triggered for PARTIALLY_COVERED, VAGUE, or HIGH-severity requirements."""
        clauses_text = "\n---\n".join(matched_clauses[:5]) if matched_clauses else "(no matching clauses found)"

        prompt = f"""Determine whether a BCR requirement is substantively met.

BCR Type: {bcr_type}
Requirement: {requirement_id} — {requirement_title}
Current rule-based status: {coverage_status}
Legal basis: {legal_basis}

Matched clauses:
{clauses_text}

Return JSON:
{{
  "coverage_status": "FULLY_COVERED" | "PARTIALLY_COVERED" | "VAGUE" | "MISSING" | "INCORRECT",
  "missing_elements": ["element1", "element2"],
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "should_generate_finding": true | false,
  "finding_text": "<if should_generate_finding, one sentence>",
  "recommendation": "<if should_generate_finding, one sentence>",
  "facts_uncertain": true | false
}}"""
        result = self._call_llm(prompt) or {
            "coverage_status": coverage_status, "missing_elements": [],
            "risk_level": "MEDIUM", "should_generate_finding": False,
            "finding_text": "", "recommendation": "", "facts_uncertain": True,
        }
        result.setdefault("coverage_status", coverage_status)
        result.setdefault("missing_elements", [])
        return result
