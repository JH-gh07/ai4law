from backend.modules.assessment.fact_builder import build_assessment_facts
from backend.modules.assessment.issue_builder import build_assessment_issues
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.schema import AssessmentRequest, RegulationHit
from backend.modules.diagnosis.schema import DiagnosisResult


def _diagnosis(path: str = "security_assessment", rule_id: str = "ciio") -> DiagnosisResult:
    return DiagnosisResult(
        recommended_path=path,
        legal_basis=["个人信息保护法 第40条"],
        rationale="规则命中",
        action_items=[],
        risk_level="HIGH",
        matched_rule_id=rule_id,
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


def _facts(request: AssessmentRequest, diagnosis: DiagnosisResult) -> list:
    profile = ProfileExtractor().extract(request)
    return build_assessment_facts(request, profile, diagnosis)


def test_ciio_important_data_and_missing_attachment_issues() -> None:
    request = AssessmentRequest(
        company_name="测试公司",
        industry="互联网医疗",
        is_ciio=True,
        contains_important_data=True,
        pii_count=100,
        spi_count=50,
        transfer_purpose="模型训练",
        receiver_country="新加坡",
        uploaded_files=[],
    )
    diagnosis = _diagnosis()

    issues = build_assessment_issues(_facts(request, diagnosis), diagnosis, _regulations(), [])
    by_id = {issue.issue_id: issue for issue in issues}

    assert "ISSUE-ciio-security-assessment" in by_id
    assert "ISSUE-important-data" in by_id
    assert "ISSUE-missing-attachments" in by_id
    assert by_id["ISSUE-ciio-security-assessment"].rule_refs[0] == "diagnosis:ciio"
    assert "reg-pipl-40" in by_id["ISSUE-important-data"].rule_refs


def test_threshold_and_path_mismatch_issues_have_fact_refs() -> None:
    request = AssessmentRequest(
        company_name="测试公司",
        industry="SaaS",
        is_ciio=False,
        contains_important_data=False,
        pii_count=1_000_000,
        spi_count=10_000,
        transfer_purpose="客服支持",
        receiver_country="新加坡",
        force_override_path=True,
        uploaded_files=[],
    )
    diagnosis = _diagnosis(path="scc_or_certification", rule_id="default")

    issues = build_assessment_issues(_facts(request, diagnosis), diagnosis, _regulations(), [])
    by_id = {issue.issue_id: issue for issue in issues}
    fact_ids = {fact.fact_id for fact in _facts(request, diagnosis)}

    assert "ISSUE-path-mismatch" in by_id
    assert "ISSUE-pii-threshold" in by_id
    assert "ISSUE-spi-threshold" in by_id
    for issue in issues:
        if issue.fact_refs:
            assert set(issue.fact_refs).issubset(fact_ids)
    # 路径/数据类 issue 应有 rule_refs
    evidence_bound = [
        issue for issue in issues
        if issue.category not in {"documentation", "legal_document", "anonymization",
                                    "onward_transfer", "internal_approval", "expression"}
    ]
    assert all(issue.rule_refs for issue in evidence_bound if issue.fact_refs)
