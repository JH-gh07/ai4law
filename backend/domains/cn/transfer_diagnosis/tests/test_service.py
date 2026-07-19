from backend.domains.cn.transfer_diagnosis.schema import DiagnosisAnswers, YesNoUnknown
from backend.domains.cn.transfer_diagnosis.service import DiagnosisService


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


def test_explicit_third_party_receiver_is_not_rewritten() -> None:
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.NO,
        q3_pii_count=100,
        q4_spi_count=0,
        q6_scenario="hr_management",
        q7_receiver_type="third_party",
    )

    normalized = service._normalize_answers(answers)
    result = service.evaluate(answers)

    assert normalized.q7_receiver_type.value == "third_party"
    assert result.matched_rule_id != "exemption_hr"


def test_conflicting_no_personal_info_is_blocked_for_manual_review() -> None:
    service = DiagnosisService()
    result = service.evaluate(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.YES,
            q3_pii_count=0,
            q4_spi_count=0,
            q5_no_personal_info=YesNoUnknown.YES,
        )
    )

    assert result.recommended_path == "manual_review"
    assert result.conclusion_source == "validation"
    assert result.requires_human_review is True


def test_agent_fact_that_triggers_rule_is_marked_and_reviewed(monkeypatch) -> None:
    service = DiagnosisService()
    monkeypatch.setattr(
        service.agents["important_data"],
        "run",
        lambda **_: {
            "result": "可能涉及重要数据",
            "confidence": 0.8,
            "suggested_answer": "yes",
        },
    )
    result = service.evaluate(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.UNKNOWN,
            q3_pii_count=0,
            q4_spi_count=0,
            q5_no_personal_info=YesNoUnknown.NO,
        )
    )

    assert result.matched_rule_id == "important_data"
    assert result.conclusion_source == "rule_with_inferred_facts"
    assert result.confidence == "MEDIUM"
    assert result.fact_provenance["contains_important_data"] == "llm_inference"
    assert result.requires_human_review is True


def test_estimated_threshold_fact_requires_review() -> None:
    service = DiagnosisService()
    result = service.evaluate(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.NO,
            q3_pii_count=0,
            q4_spi_count=0,
            m3_processes_personal_info="yes",
            m3_data_volume_range="100-1000万条",
        )
    )

    assert result.matched_rule_id == "pii_threshold"
    assert result.conclusion_source == "rule_with_inferred_facts"
    assert result.fact_provenance["personal_info_count"] == "estimate"
    assert result.requires_human_review is True
