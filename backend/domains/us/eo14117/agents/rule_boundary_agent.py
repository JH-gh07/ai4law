"""Agent 1: RuleBoundaryAgent — handles fuzzy covered person & threshold edge cases."""

from __future__ import annotations

from backend.domains.us.eo14117.agents import US14117AgentBase


class RuleBoundaryAgent(US14117AgentBase):
    """Triggered when:
    - Covered person confidence < 0.85 (uncertain inference)
    - Country not in explicit list but has concerning ownership patterns
    - Bulk threshold is at boundary (±10%)
    - Transaction type ambiguous (words don't match known patterns)
    """
    agent_name = "us14117_rule_boundary"
    max_tokens = 500

    def run(self, uncertain_entities: list[dict], boundary_items: list[dict],
            ambiguous_tx: bool, tx_description: str) -> dict:
        entity_block = "\n".join(
            f"- {e.get('entity_name','?')}: reasons={e.get('covered_person_reasons',[])} conf={e.get('confidence',0)}"
            for e in uncertain_entities[:5]
        ) or "无"
        data_block = "\n".join(
            f"- {d.get('data_item_name','?')}: {d.get('us_person_count',0)} vs threshold {d.get('bulk_threshold',0)}"
            for d in boundary_items[:5]
        ) or "无"

        prompt = f"""Review uncertain EO 14117 classifications.

Uncertain covered persons (confidence < 0.85):
{entity_block}

Threshold boundary items (±10% of threshold):
{data_block}

Ambiguous transaction type: {ambiguous_tx}
Transaction description: {tx_description[:400]}

Return JSON:
{{
  "overrides": [
    {{"entity_name": "...", "recommended_status": "confirmed|inferred|not_covered|needs_review",
      "reason": "<one sentence>", "confidence_adjustment": 0.0-1.0}}
  ],
  "flag_for_dpo": ["<item needing human review>"],
  "summary": "<one sentence overall assessment>"
}}"""
        return self._call_llm(prompt) or {
            "overrides": [], "flag_for_dpo": [],
            "summary": "Agent unavailable — boundary decisions left to rule engine.",
        }
