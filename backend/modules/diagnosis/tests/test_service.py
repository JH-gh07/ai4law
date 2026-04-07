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
