import json
from pathlib import Path

import pytest

from backend.domains.cn.transfer_diagnosis.models import DiagnosisFacts, DiagnosisPath, TriState
from backend.domains.cn.transfer_diagnosis.rule_engine import DiagnosisRuleEngine

RULE_TABLE = Path(__file__).resolve().parents[1] / "decision_tree.json"


def _engine() -> DiagnosisRuleEngine:
    return DiagnosisRuleEngine(json.loads(RULE_TABLE.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    ("overrides", "expected_rule", "expected_path"),
    [
        ({
            "no_personal_info": TriState.YES,
            "personal_info_count": 0,
            "sensitive_personal_info_count": 0,
        }, "no_personal_info", DiagnosisPath.EXEMPTION),
        ({"transfer_scenario": "contract_performance"}, "exemption_contract", DiagnosisPath.EXEMPTION),
        (
            {"transfer_scenario": "hr_management", "receiver_type": "intra_group"},
            "exemption_hr",
            DiagnosisPath.EXEMPTION,
        ),
        ({"transfer_scenario": "emergency"}, "exemption_emergency", DiagnosisPath.EXEMPTION),
        ({"transfer_scenario": "legal_duty"}, "exemption_legal_duty", DiagnosisPath.EXEMPTION),
        ({"is_ciio": TriState.YES}, "ciio", DiagnosisPath.SECURITY_ASSESSMENT),
        (
            {"contains_important_data": TriState.YES},
            "important_data",
            DiagnosisPath.SECURITY_ASSESSMENT,
        ),
        ({"personal_info_count": 1_000_000}, "pii_threshold", DiagnosisPath.SECURITY_ASSESSMENT),
        (
            {"sensitive_personal_info_count": 10_000},
            "spi_threshold",
            DiagnosisPath.SECURITY_ASSESSMENT,
        ),
        ({"personal_info_count": 999_999}, "default", DiagnosisPath.SCC_OR_CERTIFICATION),
        (
            {"sensitive_personal_info_count": 9_999},
            "default",
            DiagnosisPath.SCC_OR_CERTIFICATION,
        ),
        (
            {"is_ciio": TriState.UNKNOWN, "contains_important_data": TriState.UNKNOWN},
            "default",
            DiagnosisPath.SCC_OR_CERTIFICATION,
        ),
    ],
)
def test_rule_table_regression(
    overrides: dict,
    expected_rule: str,
    expected_path: DiagnosisPath,
) -> None:
    payload = {
        "is_ciio": TriState.NO,
        "contains_important_data": TriState.NO,
        "personal_info_count": 100,
        "sensitive_personal_info_count": 10,
    }
    payload.update(overrides)

    result = _engine().evaluate(DiagnosisFacts(**payload))

    assert result.rule_id == expected_rule
    assert result.path == expected_path


def test_rule_table_rejects_unknown_condition_key() -> None:
    with pytest.raises(ValueError, match="unsupported conditions"):
        DiagnosisRuleEngine(
            {
                "rules": [
                    {
                        "id": "typo",
                        "when": {"q2_has_importent_data": ["yes"]},
                        "path": "security_assessment",
                    }
                ],
                "default": {"path": "scc_or_certification"},
            }
        )


def test_rule_engine_blocks_conflicting_exemption_facts() -> None:
    result = _engine().evaluate(
        DiagnosisFacts(
            is_ciio=TriState.NO,
            contains_important_data=TriState.YES,
            personal_info_count=0,
            sensitive_personal_info_count=0,
            no_personal_info=TriState.YES,
        )
    )

    assert result.rule_id == "conflicting_facts"
    assert result.path == DiagnosisPath.MANUAL_REVIEW
