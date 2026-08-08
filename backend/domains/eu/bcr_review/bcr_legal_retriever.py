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

        return [self._to_reference(item) for item in hits]

    def retrieve_report_grounding(self, requirement_ids: set[str]) -> list[dict]:
        """Return only the two canonical sources supported by the local EU index."""
        selected: list[dict] = []
        try:
            gdpr_hits = retrieve_legal_documents(
                "GDPR Article 47 binding corporate rules legally binding enforceable rights",
                module="eu_bcr",
                top_k=8,
                jurisdiction="eu",
                path="all",
            ).documents
        except Exception:
            gdpr_hits = []
        article_47 = next(
            (
                item
                for item in gdpr_hits
                if item.id == "EU-LAW-001"
                and "binding corporate rules" in (item.content or "").lower()
                and "expressly confer enforceable rights" in (item.content or "").lower()
            ),
            None,
        )
        if article_47 is not None:
            selected.append(self._to_reference(article_47))

        if "BCR-C-1.9" in requirement_ids:
            try:
                tia_hits = retrieve_legal_documents(
                    "EDPB Recommendations 01/2020 six step TIA supplementary measures",
                    module="eu_bcr",
                    top_k=12,
                    jurisdiction="eu",
                    path="all",
                ).documents
            except Exception:
                tia_hits = []
            tia_step = next(
                (
                    item
                    for item in tia_hits
                    if item.id.startswith("EU-GUIDE-002")
                    and "step 3" in (item.content or "").lower()
                ),
                None,
            )
            if tia_step is not None:
                reference = self._to_reference(tia_step)
                reference["source_id"] = "EU-GUIDE-002"
                selected.append(reference)
        return selected

    @staticmethod
    def _to_reference(item) -> dict:
        article_no = normalize_article_no(item.article)
        article_label = f" 第{article_no}条" if article_no else ""
        return {
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

    @staticmethod
    def _build_query(requirement_id: str, bcr_type: str, clause_text: str) -> str:
        parts = [bcr_type or "BCR", requirement_id]
        if clause_text:
            parts.append(clause_text[:200])
        return " ".join(parts)
