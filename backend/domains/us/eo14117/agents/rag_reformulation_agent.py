"""Agent 3: RAGReformulationAgent — improves retrieval queries based on rule hits."""

from __future__ import annotations

from backend.domains.us.eo14117.agents import US14117AgentBase


class RAGReformulationAgent(US14117AgentBase):
    """Triggered when HIGH/BLOCKER issues exist — reformulates the RAG query
    to target the specific legal provisions relevant to the detected risks.
    """
    agent_name = "us14117_rag_reformulation"
    max_tokens = 400

    def run(self, rule_hit_summary: list[str], data_categories: list[str],
            transaction_type: str, covered_person_count: int) -> dict:
        hits = "; ".join(rule_hit_summary[:10])
        cats = ", ".join(data_categories[:6])

        prompt = f"""Reformulate an EO 14117 regulation retrieval query.

Rule hits detected: {hits}
Data categories involved: {cats}
Transaction type: {transaction_type}
Covered persons: {covered_person_count}

Return JSON:
{{
  "primary_query": "<targeted query for most critical provision>",
  "secondary_queries": ["<query for supporting provision>", "..."],
  "jurisdiction_hints": ["<e.g. '28 CFR § 202.301'>", "..."],
  "filter_criteria": "<what to exclude from results>"
}}"""
        return self._call_llm(prompt) or {
            "primary_query": "EO 14117 restricted transaction security measures covered person",
            "secondary_queries": [],
            "jurisdiction_hints": ["28 CFR § 202.301", "28 CFR § 202.401"],
            "filter_criteria": "",
        }
