import json
from pathlib import Path

from backend.common.risk.scoring import risk_level
from backend.modules.diagnosis.schema import DiagnosisAnswers, DiagnosisResult


class DiagnosisService:
    def __init__(self, tree_path: str | None = None) -> None:
        self.tree_path = tree_path or str(Path(__file__).with_name("decision_tree.json"))
        self._tree = self._load_tree(self.tree_path)

    @staticmethod
    def _load_tree(tree_path: str) -> dict:
        with open(tree_path, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def evaluate(self, answers: DiagnosisAnswers) -> DiagnosisResult:
        for rule in self._tree["rules"]:
            when = rule["when"]
            if self._rule_match(when, answers):
                return self._build_result(answers, rule["path"], rule["legal_basis"], rule["description"])

        default = self._tree["default"]
        return self._build_result(
            answers,
            default["path"],
            default["legal_basis"],
            "Threshold not reached for mandatory security assessment.",
        )

    @staticmethod
    def _rule_match(when: dict, answers: DiagnosisAnswers) -> bool:
        if "q1_is_ciio" in when and answers.q1_is_ciio.value not in when["q1_is_ciio"]:
            return False
        if "q2_has_important_data" in when and answers.q2_has_important_data.value not in when["q2_has_important_data"]:
            return False
        if "q3_pii_count_gte" in when and answers.q3_pii_count < int(when["q3_pii_count_gte"]):
            return False
        if "q4_spi_count_gte" in when and answers.q4_spi_count < int(when["q4_spi_count_gte"]):
            return False
        return True

    @staticmethod
    def _build_result(
        answers: DiagnosisAnswers,
        recommended_path: str,
        legal_basis: list[str],
        rationale: str,
    ) -> DiagnosisResult:
        level = risk_level(
            is_ciio=answers.q1_is_ciio.value == "yes",
            contains_important_data=answers.q2_has_important_data.value == "yes",
            pii_count=answers.q3_pii_count,
            spi_count=answers.q4_spi_count,
        )
        if recommended_path == "security_assessment":
            action_items = [
                "Prepare data export inventory and processing map.",
                "Generate Data Export Security Assessment report.",
                "Submit assessment package to CAC.",
            ]
        else:
            action_items = [
                "Choose SCC filing or certification route.",
                "Generate PIPIA report and contract appendix.",
                "Prepare provincial filing package.",
            ]

        return DiagnosisResult(
            recommended_path=recommended_path,
            legal_basis=legal_basis,
            rationale=rationale,
            action_items=action_items,
            risk_level=level,
        )
