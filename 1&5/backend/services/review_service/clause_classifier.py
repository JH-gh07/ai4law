import json
from pathlib import Path

from backend.schemas.review import Clause, ClassifiedClause, ClauseType, PartyBias


class ClauseClassifier:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parents[2] / "data" / "review_rulebook.json"
        self.rulebook = json.loads(path.read_text(encoding="utf-8"))

    def classify(self, clause: Clause) -> ClassifiedClause:
        text = clause.text
        best_type = ClauseType.OTHER
        best_keywords: list[str] = []

        for candidate, config in self.rulebook.items():
            matched = [keyword for keyword in config.get("keywords", []) if keyword in text]
            if len(matched) > len(best_keywords):
                best_type = ClauseType(candidate)
                best_keywords = matched

        return ClassifiedClause(
            **clause.model_dump(),
            clause_type=best_type,
            matched_keywords=best_keywords,
            party_bias=self._detect_party_bias(text),
        )

    def _detect_party_bias(self, text: str) -> PartyBias:
        if "乙方承担全部责任" in text or "乙方应赔偿全部损失" in text:
            return PartyBias.PARTY_A_FAVORABLE
        if "甲方承担全部责任" in text or "甲方应赔偿全部损失" in text:
            return PartyBias.PARTY_B_FAVORABLE
        return PartyBias.NEUTRAL
