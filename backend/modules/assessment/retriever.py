from __future__ import annotations

from typing import TYPE_CHECKING

from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.rag.service import (
    LegalRetrievalResult,
    LegalRetrievalService,
)
from backend.modules.assessment.schema import CompanyProfile, RegulationHit

if TYPE_CHECKING:
    from backend.services.legal_api_service import DeliLegalService


class AssessmentRetriever:
    def __init__(
        self,
        legal_service: DeliLegalService | None = None,
        retrieval_service: LegalRetrievalService | None = None,
    ) -> None:
        self.legal_service = legal_service
        self.retrieval_service = retrieval_service or LegalRetrievalService()
        self.last_bundle = None
        self.last_manifest = None

    def retrieve_context(
        self,
        request: RetrievalRequest,
        *,
        allow_legacy_fallback: bool = False,
    ) -> LegalRetrievalResult:
        if allow_legacy_fallback:
            return self.retrieval_service.retrieve_with_fallback(request)
        return self.retrieval_service.retrieve(request)

    def search(
        self,
        profile: CompanyProfile,
        top_k: int = 8,
        source: str | None = None,
    ) -> list[RegulationHit]:
        query = " ".join(
            [
                profile.industry,
                profile.transfer_purpose,
                profile.receiver_country,
                "CIIO" if profile.is_ciio else "non-CIIO",
                (
                    "important data"
                    if profile.contains_important_data
                    else "personal information"
                ),
            ]
        )
        request = RetrievalRequest(
            module="cn_assessment",
            task_stage="legal_grounding",
            query=query,
            facts=profile.model_dump(),
            environment="production",
            top_k=top_k,
            jurisdiction="cn",
            path="assessment",
        )
        result = self.retrieval_service.retrieve_with_fallback(
            request,
            retriever_options={
                "legal_service": self.legal_service,
                "source": source,
            },
        )
        self.last_bundle = result.bundle
        self.last_manifest = result.manifest
        return [
            RegulationHit(
                source_id=chunk.source_id,
                title=chunk.title,
                article=chunk.citation_anchor or chunk.article_no,
                snippet=chunk.content,
            )
            for chunk in result.bundle.legal_grounding
        ]
