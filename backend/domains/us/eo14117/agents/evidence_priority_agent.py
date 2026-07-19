"""Agent 2: EvidencePriorityAgent — ranks facts and evidence by impact on the traffic light decision."""

from __future__ import annotations

from backend.domains.us.eo14117.agents import US14117AgentBase


class EvidencePriorityAgent(US14117AgentBase):
    """Triggered when multiple data items + entities produce a large risk matrix.
    Ranks evidence items by their contribution to the RED/YELLOW outcome.
    """
    agent_name = "us14117_evidence_priority"
    max_tokens = 400

    def run(self, risk_matrix_rows: list[dict], traffic_light: str,
            prohibition_reasons: list[str], restriction_reasons: list[str]) -> dict:
        matrix_block = "\n".join(
            f"- {r.get('entity_name','?')} × {r.get('data_item_name','?')} → {r.get('traffic_light','?')} "
            f"(status={r.get('covered_person_status','?')}, threshold_hit={r.get('threshold_hit','?')})"
            for r in risk_matrix_rows[:12]
        )

        prompt = f"""Rank evidence items by their impact on the EO 14117 decision.

Overall: {traffic_light}
Prohibition reasons: {prohibition_reasons[:5]}
Restriction reasons: {restriction_reasons[:5]}

Risk matrix:
{matrix_block}

Return JSON:
{{
  "critical_evidence": ["<evidence title 1>", "<evidence title 2>"],
  "priority_order": ["entity × data pair most relevant first"],
  "diminishing_items": ["<item with low marginal impact>"],
  "recommendation": "<one sentence on what to focus the report on>"
}}"""
        return self._call_llm(prompt) or {
            "critical_evidence": [], "priority_order": [],
            "diminishing_items": [],
            "recommendation": "Agent unavailable — using flat evidence list.",
        }
