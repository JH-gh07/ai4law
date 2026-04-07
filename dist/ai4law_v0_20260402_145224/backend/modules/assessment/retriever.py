from backend.common.rag.retriever import retrieve_regulations
from backend.modules.assessment.schema import CompanyProfile, RegulationHit


class AssessmentRetriever:
    def search(self, profile: CompanyProfile, top_k: int = 8) -> list[RegulationHit]:
        query = " ".join(
            [
                profile.industry,
                profile.transfer_purpose,
                profile.receiver_country,
                "CIIO" if profile.is_ciio else "non-CIIO",
                "important data" if profile.contains_important_data else "personal information",
            ]
        )
        docs = retrieve_regulations(query, top_k=top_k)
        return [
            RegulationHit(
                source_id=doc.id,
                title=doc.title,
                article=doc.article,
                snippet=doc.content,
            )
            for doc in docs
        ]
