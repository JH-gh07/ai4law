"""BCRLegalRetriever — issue-aware GDPR/EDPB regulation retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.common.rag.service import retrieve_legal_documents

if TYPE_CHECKING:
    from backend.integrations.delilegal import DeliLegalService


class BCRLegalRetriever:
    def __init__(self, legal_service: DeliLegalService | None = None) -> None:
        self.legal_service = legal_service

    def retrieve(self, requirement_id: str, bcr_type: str, clause_text: str) -> list[dict]:
        query = self._build_query(requirement_id, bcr_type, clause_text)
        try:
            hits = retrieve_legal_documents(
                query,
                module="eu_bcr",
                top_k=3,
                jurisdiction="eu",
                path="all",
            ).documents
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
