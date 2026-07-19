"""Agent 8: BCRLegalGroundingAgent — validate that citations actually support findings.

Classifies citations as primary (directly supports finding), supporting (provides
context), or discarded (irrelevant). Uses a built-in article-to-requirement map.
"""

from __future__ import annotations

import re

from backend.domains.eu.bcr_review.agents import BCRAgentBase


class BCRLegalGroundingAgent(BCRAgentBase):
    agent_name = "bcr_legal_grounding"
    max_tokens = 400

    # Requirement → required legal basis map
    _REQUIREMENT_LEGAL_MAP: dict[str, list[dict]] = {
        "BCR-C-1.1": [
            {"source": "GDPR", "article": "47(1)(a)", "role": "primary"},
            {"source": "EDPB", "article": "Recommendations 1/2022", "role": "supporting"},
        ],
        "BCR-C-1.2": [
            {"source": "GDPR", "article": "47(1)(b)", "role": "primary"},
            {"source": "EDPB", "article": "Recommendations 1/2022 §5.2", "role": "supporting"},
        ],
        "BCR-C-1.3": [
            {"source": "GDPR", "article": "47(1)(f)", "role": "primary"},
            {"source": "GDPR", "article": "47(2)(a)", "role": "supporting"},
        ],
        "BCR-C-1.4": [
            {"source": "GDPR", "article": "47(1)(f)", "role": "primary"},
            {"source": "GDPR", "article": "82", "role": "supporting"},
        ],
        # Default for unknown requirements
        "_default": [
            {"source": "GDPR", "article": "47", "role": "supporting"},
            {"source": "EDPB", "article": "Recommendations 1/2022", "role": "supporting"},
        ],
    }

    # Known valid citation sources for BCR review
    _VALID_SOURCES = {
        "GDPR", "EDPB", "Schrems II", "C-311/18", "WP29", "WP256", "WP257",
        "EU 2021/914", "SCC", "Data Protection Act", "BDSG", "ICO",
    }

    def run(self, finding_id: str, requirement_id: str,
            rag_citations: list[dict], clause_text: str = "",
            bcr_type: str = "BCR-C") -> dict:
        """Validate that RAG-returned citations actually support the finding.

        Returns triaged citations: primary_basis, supporting_basis, discarded_basis.
        """
        required_basis = self._REQUIREMENT_LEGAL_MAP.get(
            requirement_id,
            self._REQUIREMENT_LEGAL_MAP["_default"]
        )

        primary_basis: list[dict] = []
        supporting_basis: list[dict] = []
        discarded_basis: list[dict] = []

        for cite in rag_citations:
            source = (cite.get("source") or cite.get("title") or "").lower()
            article = (cite.get("article") or cite.get("section") or "").lower()

            # ── Check against required legal basis ──
            matched_role = None
            for req in required_basis:
                req_source = req["source"].lower()
                req_article = req["article"].lower()
                if req_source in source or source in req_source:
                    if req_article in article or article in req_article:
                        matched_role = req["role"]
                        break
                    elif not req_article:
                        matched_role = req["role"]

            if matched_role == "primary":
                primary_basis.append({
                    "source": cite.get("source", cite.get("title", "")),
                    "article": cite.get("article", cite.get("section", "")),
                    "used_for": f"Supports finding {finding_id} on {requirement_id}",
                })
            elif matched_role == "supporting" or self._is_valid_source(source):
                supporting_basis.append({
                    "source": cite.get("source", cite.get("title", "")),
                    "article": cite.get("article", cite.get("section", "")),
                    "used_for": f"Provides context for finding {finding_id}",
                })
            else:
                discarded_basis.append({
                    "source": cite.get("source", cite.get("title", "")),
                    "article": cite.get("article", cite.get("section", "")),
                    "reason": (
                        f"Source '{cite.get('source', cite.get('title', ''))}' "
                        f"does not match required legal basis for {requirement_id}"
                    ),
                })

        # ── Determine grounding adequacy ──
        grounding_adequate = len(primary_basis) >= 1 or len(supporting_basis) >= 1

        # ── LLM enhancement if grounding is weak ──
        if not grounding_adequate and rag_citations:
            llm_result = self._try_llm_grounding(finding_id, requirement_id, rag_citations, bcr_type)
            if llm_result:
                if llm_result.get("primary_basis"):
                    primary_basis.extend(llm_result["primary_basis"])
                    grounding_adequate = True

        return {
            "finding_id": finding_id,
            "requirement_id": requirement_id,
            "grounding_adequate": grounding_adequate,
            "primary_basis": primary_basis,
            "supporting_basis": supporting_basis,
            "discarded_basis": discarded_basis,
            "total_citations": len(rag_citations),
            "discarded_count": len(discarded_basis),
        }

    @staticmethod
    def _is_valid_source(source: str) -> bool:
        """Check if source is a recognized EU data protection authority or instrument."""
        valid_keywords = [
            "gdpr", "edpb", "dp", "data protection", "privacy", "data privacy",
            "regulation", "directive", "adequacy", "scc", "standard contractual",
            "binding corporate", "bcr", "schrems", "article 29", "wp29",
            "european data", "eu data", "commission", "supervisory",
        ]
        return any(kw in source.lower() for kw in valid_keywords)

    def _try_llm_grounding(self, finding_id: str, req_id: str,
                            citations: list[dict], bcr_type: str) -> dict | None:
        cites_json = str([{"source": c.get("source", ""), "article": c.get("article", "")}
                          for c in citations[:5]])
        prompt = f"""Validate whether these citations support a BCR finding.

BCR Type: {bcr_type}
Finding: {finding_id}
Requirement: {req_id}
Citations: {cites_json}

Return JSON:
{{
  "grounding_adequate": true | false,
  "primary_basis": [{{"source": "<source>", "article": "<article>", "used_for": "<reason>"}}],
  "recommended_citation": "<if grounding is weak, suggest specific citation>"
}}"""
        return self._call_llm(prompt)
