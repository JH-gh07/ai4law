from backend.modules.diagnosis.schema import DiagnosisAnswers, YesNoUnknown
from backend.modules.diagnosis.service import DiagnosisService


def test_diagnosis_security_assessment_by_pii_threshold() -> None:
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.NO,
        q3_pii_count=1_100_000,
        q4_spi_count=200,
        q8_purpose="marketing analytics",
    )

    result = service.evaluate(answers)
    assert result.recommended_path == "security_assessment"


def test_diagnosis_scc_path() -> None:
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.NO,
        q3_pii_count=50_000,
        q4_spi_count=200,
        q8_purpose="customer support",
    )

    result = service.evaluate(answers)
    assert result.recommended_path == "scc_or_certification"


def test_diagnosis_new_questionnaire_fields_drive_important_data_path() -> None:
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.UNKNOWN,
        q3_pii_count=0,
        q4_spi_count=0,
        q5_no_personal_info=YesNoUnknown.UNKNOWN,
        m3_processes_personal_info="yes",
        m3_processes_important_data="yes",
        m3_important_data_types=["金融交易数据"],
        m3_data_volume_range="10-100万条",
    )

    result = service.evaluate(answers)
    assert result.recommended_path == "security_assessment"
    assert result.matched_rule_id == "important_data"


def test_diagnosis_new_questionnaire_fields_can_match_exemption() -> None:
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.UNKNOWN,
        q3_pii_count=0,
        q4_spi_count=0,
        q5_no_personal_info=YesNoUnknown.UNKNOWN,
        q6_scenario="contract_performance",
        m3_processes_personal_info="no",
        m3_processes_important_data="no",
    )

    result = service.evaluate(answers)
    assert result.recommended_path == "exemption"
    assert result.matched_rule_id == "no_personal_info"
