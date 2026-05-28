from backend.modules.assessment.fact_builder import build_assessment_facts
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.schema import AssessmentRequest
from backend.modules.diagnosis.schema import DiagnosisResult


def test_assessment_facts_include_core_fields() -> None:
    request = AssessmentRequest(
        company_name="测试公司",
        industry="互联网医疗",
        is_ciio=True,
        contains_important_data=True,
        pii_count=20000,
        spi_count=12000,
        transfer_purpose="模型训练",
        receiver_country="新加坡",
        uploaded_files=["policy.pdf"],
    )
    profile = ProfileExtractor().extract(request)
    diagnosis = DiagnosisResult(
        recommended_path="security_assessment",
        legal_basis=["个人信息保护法 第40条"],
        rationale="CIIO must apply for security assessment",
        action_items=[],
        risk_level="HIGH",
        matched_rule_id="ciio",
    )

    facts = build_assessment_facts(request, profile, diagnosis)
    by_field = {fact.field_path: fact for fact in facts}

    assert "request.receiver_country" in by_field
    assert "request.is_ciio" in by_field
    assert "request.contains_important_data" in by_field
    assert "diagnosis_result.recommended_path" in by_field
    assert by_field["request.receiver_country"].value == "新加坡"
    assert by_field["diagnosis_result.recommended_path"].value == "security_assessment"


def test_assessment_facts_do_not_dump_entire_request() -> None:
    request = AssessmentRequest(
        company_name="测试公司",
        industry="互联网医疗",
        is_ciio=False,
        contains_important_data=False,
        pii_count=1,
        spi_count=0,
        transfer_purpose="客服支持",
        receiver_country="新加坡",
    )
    profile = ProfileExtractor().extract(request)

    facts = build_assessment_facts(request, profile, diagnosis_result=None)

    assert all(fact.value != request.model_dump() for fact in facts)
    assert {fact.fact_id for fact in facts}
