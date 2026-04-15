import json
from pathlib import Path

from backend.common.risk.scoring import risk_level
from backend.modules.diagnosis.schema import DiagnosisAnswers, DiagnosisResult


_RATIONALE_I18N = {
    "CIIO must apply for security assessment": "企业被识别为关键信息基础设施运营者，应优先走安全评估路径。",
    "Important data export must apply for security assessment": "涉及重要数据出境，按监管要求应优先走安全评估路径。",
    "PII count >= 1,000,000 must apply for security assessment": "个人信息处理规模达到法定门槛，应优先走安全评估路径。",
    "Sensitive PII count >= 10,000 must apply for security assessment": "敏感个人信息处理规模达到法定门槛，应优先走安全评估路径。",
    "Threshold not reached for mandatory security assessment.": "未触发强制安全评估门槛，可走标准合同备案或认证路径。",
}


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
            _RATIONALE_I18N["Threshold not reached for mandatory security assessment."],
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
        if "q3_pii_count_lt" in when and answers.q3_pii_count >= int(when["q3_pii_count_lt"]):
            return False
        if "q4_spi_count_lt" in when and answers.q4_spi_count >= int(when["q4_spi_count_lt"]):
            return False
        if "q5_no_personal_info" in when and answers.q5_no_personal_info.value not in when["q5_no_personal_info"]:
            return False
        if "q6_scenario" in when and answers.q6_scenario.value not in when["q6_scenario"]:
            return False
        if "q7_receiver_type" in when and answers.q7_receiver_type.value not in when["q7_receiver_type"]:
            return False
        return True

    @staticmethod
    def _build_result(
        answers: DiagnosisAnswers,
        recommended_path: str,
        legal_basis: list[str],
        rationale: str,
    ) -> DiagnosisResult:
        rationale = _RATIONALE_I18N.get(rationale, rationale)
        level = risk_level(
            is_ciio=answers.q1_is_ciio.value == "yes",
            contains_important_data=answers.q2_has_important_data.value == "yes",
            pii_count=answers.q3_pii_count,
            spi_count=answers.q4_spi_count,
        )
        if recommended_path == "security_assessment":
            action_items = [
                "整理数据出境清单与处理活动映射。",
                "生成《数据出境风险自评估报告》草案并补齐附件。",
                "按属地网信要求提交安全评估申报材料。",
            ]
        else:
            action_items = [
                "在标准合同备案与个人信息保护认证之间确定实施路径。",
                "生成 PIPIA 报告及标准合同配套附件。",
                "准备省级网信备案/留档材料并完成内部审批。",
            ]

        return DiagnosisResult(
            recommended_path=recommended_path,
            legal_basis=legal_basis,
            rationale=rationale,
            action_items=action_items,
            risk_level=level,
        )
