import json
from pathlib import Path

from backend.common.rag.retriever import retrieve_regulations
from backend.schemas.review import ClauseType
from backend.services.legal_api_service import DeliLegalService


class LocalRegulationKnowledgeBase:
    def __init__(self, legal_api_service: DeliLegalService | None = None) -> None:
        path = Path(__file__).resolve().parents[2] / "data" / "review_rulebook.json"
        self.rulebook = json.loads(path.read_text(encoding="utf-8"))
        self.legal_api_service = legal_api_service

    def lookup(self, clause_type: ClauseType, clause_text: str | None = None) -> dict:
        if clause_type.value in self.rulebook:
            config = dict(self.rulebook[clause_type.value])
        else:
            config = {
                "display_name": "Other Clause",
                "required_groups": [],
                "citations": ["Personal Information Protection Law and related rules"],
            }

        rag_citations: list[str] = []
        if clause_text:
            rag_hits = retrieve_regulations(
                query=f"{config.get('display_name', clause_type.value)} {clause_text[:400]}",
                top_k=3,
                jurisdiction="cn",
                path="review",
                mode="hybrid",
                legal_service=self.legal_api_service,
            )
            rag_citations = [
                f"{item.title}{item.article}".strip()
                for item in rag_hits
                if item.title or item.article
            ]

        citations = list(config.get("citations", []))
        if rag_citations:
            citations = list(dict.fromkeys([*citations, *rag_citations]))

        if self.legal_api_service and self.legal_api_service.enabled and clause_text:
            hits = self.legal_api_service.search_cases(clause_text[:80], size=2)
            if hits:
                external_citations = [
                    f"{item['source']}: {item['title']}"
                    for item in hits
                ]
                citations = list(dict.fromkeys([*citations, *external_citations]))
            elif self.legal_api_service.last_error:
                citations = list(
                    dict.fromkeys(
                        [
                            *citations,
                            f"DeliLegal API failed: {self.legal_api_service.last_error}",
                        ]
                    )
                )

        config["citations"] = citations
        return config
