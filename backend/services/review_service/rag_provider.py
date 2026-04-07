import json
from pathlib import Path

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

        if self.legal_api_service and self.legal_api_service.enabled and clause_text:
            hits = self.legal_api_service.search_cases(clause_text[:80], size=2)
            if hits:
                external_citations = [
                    f"{item['source']}：{item['title']}" for item in hits
                ]
                config["citations"] = list(dict.fromkeys([*config.get("citations", []), *external_citations]))
            elif self.legal_api_service.last_error:
                config["citations"] = list(
                    dict.fromkeys(
                        [
                            *config.get("citations", []),
                            f"得理API调用失败：{self.legal_api_service.last_error}",
                        ]
                    )
                )
        return config
