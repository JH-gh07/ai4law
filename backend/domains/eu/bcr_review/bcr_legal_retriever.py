"""BCRLegalRetriever — issue-aware GDPR/EDPB regulation retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.common.citation.locators import normalize_article_no
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

        references: list[dict] = []
        for item in hits:
            article_no = normalize_article_no(item.article)
            article_label = f" 第{article_no}条" if article_no else ""
            references.append(
                {
                    # Keep the original public keys for clause reviewers, while
                    # retaining the full record needed by the report registry.
                    "source": f"{item.title}{article_label}",
                    "section": item.article,
                    "snippet": (item.content or "")[:200],
                    "source_id": item.id,
                    "title": item.title,
                    "article": item.article,
                    "content": item.content,
                    "jurisdiction": item.jurisdiction or "eu",
                    "source_url": item.source_url,
                }
            )
        return references

    @staticmethod
    def _build_query(requirement_id: str, bcr_type: str, clause_text: str) -> str:
        parts = [bcr_type or "BCR", requirement_id]
        if clause_text:
            parts.append(clause_text[:200])
        return " ".join(parts)
