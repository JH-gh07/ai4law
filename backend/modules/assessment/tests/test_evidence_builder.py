from backend.modules.assessment.evidence_builder import build_assessment_evidence
from backend.modules.assessment.fact_builder import build_assessment_facts
from backend.modules.assessment.issue_builder import build_assessment_issues
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.schema import AssessmentRequest, RegulationHit
from backend.modules.diagnosis.schema import DiagnosisResult


def _diagnosis() -> DiagnosisResult:
    return DiagnosisResult(
        recommended_path="security_assessment",
        legal_basis=["个人信息保护法 第40条"],
        rationale="规则命中",
        action_items=[],
        risk_level="HIGH",
        matched_rule_id="ciio",
    )


def _regulations() -> list[RegulationHit]:
    return [
        RegulationHit(
            source_id="reg-pipl-40",
            title="个人信息保护法",
            article="第40条",
            snippet="CIIO 或达到规模的个人信息处理者向境外提供个人信息应满足要求。",
        )
    ]


def test_ciio_issue_produces_evidence_with_ciio_fact_ref() -> None:
    request = AssessmentRequest(
        company_name="测试公司",
        industry="互联网医疗",
        is_ciio=True,
        contains_important_data=False,
        pii_count=100,
        spi_count=50,
        transfer_purpose="模型训练",
        receiver_country="新加坡",
        uploaded_files=[],
    )
    diagnosis = _diagnosis()
    profile = ProfileExtractor().extract(request)
    facts = build_assessment_facts(request, profile, diagnosis)
    issues = build_assessment_issues(facts, diagnosis, _regulations(), [])

    updated_issues, evidence_chain = build_assessment_evidence(facts, issues, _regulations(), diagnosis)

    ciio_fact = next(fact for fact in facts if fact.field_path == "request.is_ciio")
    assert any(ciio_fact.fact_id in evidence.fact_refs for evidence in evidence_chain)
    assert any("CIIO" in evidence.claim for evidence in evidence_chain)
    assert all(evidence.fact_refs for evidence in evidence_chain)

    evidence_ids = {evidence.evidence_id for evidence in evidence_chain}
    for issue in updated_issues:
        assert issue.evidence_refs
        assert set(issue.evidence_refs).issubset(evidence_ids)


def test_regulatory_evidence_has_rule_refs_material_evidence_can_omit_them() -> None:
    request = AssessmentRequest(
        company_name="测试公司",
        industry="互联网医疗",
        is_ciio=True,
        contains_important_data=True,
        pii_count=1_000_000,
        spi_count=10_000,
        transfer_purpose="模型训练",
        receiver_country="新加坡",
        uploaded_files=[],
    )
    diagnosis = _diagnosis()
    profile = ProfileExtractor().extract(request)
    facts = build_assessment_facts(request, profile, diagnosis)
    issues = build_assessment_issues(facts, diagnosis, _regulations(), [])

    _, evidence_chain = build_assessment_evidence(facts, issues, _regulations(), diagnosis)

    for evidence in evidence_chain:
        if evidence.evidence_id == "EVIDENCE-missing-attachments":
            assert evidence.rule_refs == []
        else:
            assert evidence.rule_refs
