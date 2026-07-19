"""Agent 1: RAGPlanningAgent — decomposes TIA into targeted legal queries."""

from __future__ import annotations

from backend.domains.eu.tia.agents import TIAAgentBase


class RAGPlanningAgent(TIAAgentBase):
    """Generates multiple targeted legal-retrieval queries based on TIA context.

    Replaces the single generic query with domain-specific queries for:
    - Transfer tool legal basis
    - Destination country law risks
    - Supplementary measure adequacy
    - Data sensitivity implications
    """
    agent_name = "tia_rag_planning"
    max_tokens = 500

    def run(self, transfer_tool: str, dest_country: str, data_categories: list[str],
            sensitivity: str, country_risk_level: str, has_spi: bool,
            gov_access_risk: bool, route: str) -> dict:
        cats = ", ".join(data_categories[:6]) if data_categories else "unspecified"

        prompt = f"""Plan RAG retrieval queries for a Transfer Impact Assessment.

Transfer tool: {transfer_tool}
Destination: {dest_country}
Data categories: {cats}
Sensitivity: {sensitivity}
Country risk level: {country_risk_level}
Has special category data: {has_spi}
Government access risk: {gov_access_risk}
Route: {route}

Return JSON:
{{
  "queries": [
    {{"purpose": "transfer_tool_legal_basis", "query": "GDPR Article 46 international transfer SCC BCR legal basis"}},
    {{"purpose": "destination_law_risk", "query": "{dest_country} government access surveillance law personal data Schrems II"}},
    {{"purpose": "supplementary_measures", "query": "EDPB 01/2020 supplementary measures encryption key management technical"}},
    {{"purpose": "data_protection", "query": "GDPR Article 9 special category {cats} transfer safeguards"}},
    {{"purpose": "remedy_oversight", "query": "{dest_country} independent oversight judicial remedy data protection"}}
  ],
  "priority_order": ["transfer_tool_legal_basis", "destination_law_risk", "supplementary_measures"]
}}"""

        # Agent unavailable → fallback to heuristic query generation
        fallback = {
            "queries": [
                {"purpose": "transfer_tool", "query": f"GDPR Article 46 {transfer_tool} international transfer legal basis"},
                {"purpose": "destination_law", "query": f"{dest_country} government access surveillance personal data Schrems II"},
                {"purpose": "supplementary", "query": "EDPB Recommendations 01/2020 supplementary measures encryption"},
                {"purpose": "data_sensitivity", "query": f"GDPR Article 9 special category personal data {cats}"},
            ],
            "priority_order": ["transfer_tool", "destination_law", "supplementary"],
        }
        return self._call_llm(prompt) or fallback
