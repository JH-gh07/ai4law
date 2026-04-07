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
                "display_name": "其他条款",
                "required_groups": [],
                "citations": ["《个人信息保护法》相关规定"],
            }

        rag_citations: list[str] = []
        if clause_text:
            rag_hits = retrieve_regulations(
                query=f"{config.get('display_name', clause_type.value)} {clause_text[:400]}",
                top_k=3,
                jurisdiction="cn",
                path="review",
                mode="hybrid",
            )
            rag_citations = [
                f"{item.title}{item.article}".strip()
                for item in rag_hits
                if item.title or item.article
            ]

        if self.legal_api_service and self.legal_api_service.enabled and clause_text:
            hits = self.legal_api_service.search_cases(clause_text[:80], size=2)
            if hits:
                external_citations = [
                    f"{item['source']}：{item['title']}"
                    for item in hits
                ]
                config["citations"] = list(
                    dict.fromkeys([*config.get("citations", []), *rag_citations, *external_citations])
                )
                return config

        if rag_citations:
            config["citations"] = list(dict.fromkeys([*config.get("citations", []), *rag_citations]))

        return config
