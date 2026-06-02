"""Agent 3: BCRActorRoleAgent — entity role identification beyond regex."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRActorRoleAgent(BCRAgentBase):
    agent_name = "bcr_actor_role"
    max_tokens = 600

    def run(self, text: str, entities: list[dict]) -> dict:
        entity_list = "\n".join(
            f"- {e.get('name', '?')}: {e.get('context', '')[:120]}"
            for e in entities[:10]
        )
        prompt = f"""Identify the roles of each entity in this BCR document.

Extracted entities and surrounding context:
{entity_list}

Text excerpt (relevant sections):
{text[:5000]}

Return JSON:
{{
  "entities": [
    {{
      "name": "Entity Name",
      "location": "country/city",
      "roles": ["EU responsible entity", "BCR member", "data exporter", "data importer", ...],
      "evidence": "quote from text",
      "confidence": 0.0-1.0
    }}
  ],
  "eu_liable_entity": "name or null",
  "has_clear_eu_liable_entity": true | false,
  "risk_if_missing": "LOW" | "MEDIUM" | "HIGH"
}}"""
        result = self._call_llm(prompt) or {
            "entities": entities, "eu_liable_entity": None,
            "has_clear_eu_liable_entity": False, "risk_if_missing": "HIGH",
        }
        result.setdefault("entities", entities)
        return result
