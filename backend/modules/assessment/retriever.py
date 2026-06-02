from __future__ import annotations

from typing import TYPE_CHECKING

from backend.common.rag.retriever import retrieve_regulations
from backend.modules.assessment.schema import CompanyProfile, RegulationHit

if TYPE_CHECKING:
    from backend.services.legal_api_service import DeliLegalService


class AssessmentRetriever:
    def __init__(self, legal_service: DeliLegalService | None = None) -> None:
        self.legal_service = legal_service

    def search(self, profile: CompanyProfile, top_k: int = 8, source: str | None = None) -> list[RegulationHit]:
        query = " ".join(
            [
                profile.industry,
                profile.transfer_purpose,
                profile.receiver_country,
                "CIIO" if profile.is_ciio else "non-CIIO",
                "important data" if profile.contains_important_data else "personal information",
            ]
        )
        docs = retrieve_regulations(
            query,
            top_k=top_k,
            jurisdiction="cn",
            path="assessment",
            legal_service=self.legal_service,
            source=source,
        )
        return [
            RegulationHit(
                source_id=doc.id,
                title=doc.title,
                article=doc.article,
                snippet=doc.content,
            )
            for doc in docs
        ]
