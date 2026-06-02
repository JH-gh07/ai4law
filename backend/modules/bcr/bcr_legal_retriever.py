"""BCRLegalRetriever — issue-aware GDPR/EDPB regulation retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.legal_api_service import DeliLegalService


class BCRLegalRetriever:
    def __init__(self, legal_service: DeliLegalService | None = None) -> None:
        self.legal_service = legal_service

    def retrieve(self, requirement_id: str, bcr_type: str, clause_text: str) -> list[dict]:
        from backend.common.rag.retriever import retrieve_regulations

        query = self._build_query(requirement_id, bcr_type, clause_text)
        try:
            hits = retrieve_regulations(query, top_k=3, jurisdiction="eu", path="all")
        except Exception:
            return []

        return [
            {"source": f"{item.title}{item.article}", "section": item.article,
             "snippet": (item.content or "")[:200]}
            for item in hits
        ]

    @staticmethod
    def _build_query(requirement_id: str, bcr_type: str, clause_text: str) -> str:
        parts = [bcr_type or "BCR", requirement_id]
        if clause_text:
            parts.append(clause_text[:200])
        return " ".join(parts)
