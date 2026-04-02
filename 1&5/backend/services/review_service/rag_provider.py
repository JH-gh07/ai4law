import json
from pathlib import Path

from backend.schemas.review import ClauseType, ContractType, ReviewStance
from backend.services.legal_api_service import DeliLegalService


class LocalRegulationKnowledgeBase:
    def __init__(self, legal_api_service: DeliLegalService | None = None) -> None:
        path = Path(__file__).resolve().parents[2] / "data" / "review_rulebook.json"
        self.rulebook = json.loads(path.read_text(encoding="utf-8"))
        self.legal_api_service = legal_api_service

    def lookup(
        self,
        clause_type: ClauseType,
        clause_text: str | None = None,
        contract_type: ContractType | None = None,
        review_stance: ReviewStance | None = None,
    ) -> dict:
        config = dict(
            self.rulebook.get(
                clause_type.value,
                {
                    "display_name": "其他条款",
                    "required_groups": [],
                    "citations": ["《个人信息保护法》的一般合规要求"],
                },
            )
        )

        if contract_type == ContractType.PERSONAL_INFO_SCC:
            config["citations"] = list(
                dict.fromkeys(
                    [*config.get("citations", []), "《个人信息出境标准合同》及其备案指南"]
                )
            )
        if review_stance == ReviewStance.PARTY_B:
            config["stance_focus"] = "重点识别责任过重、审计范围过宽、时限过短等乙方风险。"
        else:
            config["stance_focus"] = "重点识别控制权不足、审计权不足、追偿权不足等甲方风险。"

        if self.legal_api_service and self.legal_api_service.enabled and clause_text:
            hits = self.legal_api_service.search_cases(clause_text[:80], size=2)
            if hits:
                external = [f"{item['source']}：{item['title']}" for item in hits]
                config["citations"] = list(dict.fromkeys([*config.get("citations", []), *external]))

        return config
