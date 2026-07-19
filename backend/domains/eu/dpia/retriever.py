"""DPIA regulation retrieval through the shared legal retrieval boundary."""

from __future__ import annotations

from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.rag.service import LegalRetrievalService
from backend.domains.eu.dpia.schema import DPIAProjectProfile, RegulationHit


class DPIARetriever:
    def __init__(
        self,
        retrieval_service: LegalRetrievalService | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or LegalRetrievalService()
        self.last_bundle = None
        self.last_manifest = None

    def search(
        self,
        profile: DPIAProjectProfile,
        top_k: int = 8,
    ) -> list[RegulationHit]:
        parts: list[str] = [
            "DPIA GDPR Article 35",
            profile.project_goal,
            profile.processing_flow_description,
        ]
        if profile.special_category_data:
            parts.append("special category data Article 9")
        if profile.automated_decision_making:
            parts.append("automated decision making Article 22")
        if profile.systematic_monitoring:
            parts.append("systematic monitoring WP248")
        if profile.cross_border_transfer:
            parts.append(
                f"cross border transfer {profile.transfer_destination}"
            )
        if profile.lawful_basis:
            parts.extend(profile.lawful_basis)
        query = " ".join(parts)

        result = self.retrieval_service.retrieve_with_fallback(
            RetrievalRequest(
                module="eu_dpia",
                task_stage="legal_grounding",
                query=query,
                facts=profile.model_dump(),
                environment="production",
                top_k=top_k,
                jurisdiction="eu",
                path="dpia",
            )
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
