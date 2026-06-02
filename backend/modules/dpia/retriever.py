"""DPIA regulation retriever — searches EU GDPR knowledge base for DPIA-relevant regulations."""

from __future__ import annotations

from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.rag.orchestrator import RetrievalOrchestrator
from backend.common.rag.retriever import retrieve_regulations
from backend.modules.dpia.schema import DPIAProjectProfile, RegulationHit


class DPIARetriever:
    """Retrieve GDPR / WP29 / ICO / EDPB regulations relevant to the DPIA."""

    def __init__(self) -> None:
        self._orchestrator = RetrievalOrchestrator()
        self.last_bundle = None

    def search(self, profile: DPIAProjectProfile, top_k: int = 8) -> list[RegulationHit]:
        # Build a DPIA-relevant query from processing profile
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
            parts.append(f"cross border transfer {profile.transfer_destination}")
        if profile.lawful_basis:
            parts.extend(profile.lawful_basis)
        query = " ".join(parts)

        self.last_bundle = self._orchestrator.retrieve(
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

        docs = retrieve_regulations(
            query,
            top_k=top_k,
            jurisdiction="eu",
            path="dpia",
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
