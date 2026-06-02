"""Agent 1: BCRTypeReasoningAgent — resolve ambiguous BCR-C vs BCR-P."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRTypeReasoningAgent(BCRAgentBase):
    agent_name = "bcr_type_reasoning"
    max_tokens = 500

    def run(self, text: str, declared_type: str, c_score: float, p_score: float,
            c_evidence: list[str], p_evidence: list[str]) -> dict:
        """Triggered when actual=unknown or c_score and p_score are close (<2.0 apart)."""
        if abs(c_score - p_score) < 2.0:
            trigger = "scores_too_close"
        else:
            trigger = "actual_unknown"

        prompt = f"""Determine the correct BCR type based on text analysis.

Declared type: {declared_type}
C-score: {c_score} (signals: {c_evidence[:5]})
P-score: {p_score} (signals: {p_evidence[:5]})
Trigger reason: {trigger}

Text excerpt (first 3000 chars):
{text[:3000]}

Return JSON:
{{
  "type_judgment": "BCR-C" | "BCR-P" | "mixed" | "unknown",
  "confidence": 0.0-1.0,
  "reasoning_summary": "<1 sentence>",
  "recommended_path": "<1 sentence action>",
  "risk_level": "LOW" | "MEDIUM" | "HIGH"
}}"""
        result = self._call_llm(prompt) or {
            "type_judgment": "unknown", "confidence": 0.3,
            "reasoning_summary": "Agent unavailable — falling back to keyword scoring.",
            "recommended_path": "Manual review required.", "risk_level": "MEDIUM",
        }
        result.setdefault("type_judgment", "unknown")
        result.setdefault("confidence", 0.3)
        return result
