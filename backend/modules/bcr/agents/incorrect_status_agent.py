"""Agent 7: BCRIncorrectStatusAgent — detect "written but wrong" patterns."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRIncorrectStatusAgent(BCRAgentBase):
    agent_name = "bcr_incorrect_status"
    max_tokens = 400

    def run(self, clause_text: str, requirement_id: str, requirement_title: str,
            bcr_type: str, mismatch_signals: list[str]) -> dict:
        prompt = f"""Determine if this clause is INCORRECT (not just missing/vague) for a {bcr_type} BCR.

Requirement: {requirement_id} — {requirement_title}
Clause: {clause_text[:800]}
Mismatch signals (from rule layer): {mismatch_signals}

Return JSON:
{{
  "coverage_status": "INCORRECT" | "PARTIALLY_COVERED" | "VAGUE",
  "finding": "<one sentence explaining why it's wrong, if INCORRECT>",
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "recommendation": "<one sentence correction>"
}}"""
        result = self._call_llm(prompt) or {
            "coverage_status": "PARTIALLY_COVERED", "finding": "", "risk_level": "MEDIUM", "recommendation": "",
        }
        result.setdefault("coverage_status", "PARTIALLY_COVERED")
        return result
