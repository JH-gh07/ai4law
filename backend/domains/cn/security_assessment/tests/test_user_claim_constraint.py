from backend.common.workflow import FactItem, GenerationContextPack
from backend.domains.cn.security_assessment.consistency_checker import check_user_claim_positive_statement


def test_user_claim_only_fact_with_positive_marker_triggers_flag() -> None:
    fact = FactItem(
        fact_id="FACT-request-transfer_purpose",
        source_type="schema",
        field_path="request.transfer_purpose",
        value="模型训练与数据分析",
        normalized_value="模型训练与数据分析",
        evidence_status="user_claim_only",
        can_support_external_positive_claim=False,
    )
    pack = GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[fact],
        diagnosis_result={},
        regulations=[],
        issues=[],
    )
    report = (
        "企业以模型训练与数据分析为目的向境外传输数据，"
        "已充分证明其必要性，完全合规，数据管理无风险。"
    )
    issues = check_user_claim_positive_statement(report, pack)
    assert len(issues) >= 1
    assert any("user_claim_only" in i for i in issues)


def test_documented_evidence_fact_with_positive_marker_does_not_flag() -> None:
    fact = FactItem(
        fact_id="FACT-diagnosis-recommended_path",
        source_type="diagnosis",
        field_path="diagnosis_result.recommended_path",
        value="security_assessment",
        normalized_value="security_assessment",
        evidence_status="documented_evidence",
        can_support_external_positive_claim=True,
    )
    pack = GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[fact],
        diagnosis_result={},
        regulations=[],
        issues=[],
    )
    report = "经评估，推荐安全评估路径，符合合规要求。"
    issues = check_user_claim_positive_statement(report, pack)
    # documented_evidence facts with can_support_external_positive_claim=True should not flag
    assert issues == []


def test_user_claim_fact_without_positive_marker_does_not_flag() -> None:
    fact = FactItem(
        fact_id="FACT-request-pii_count",
        source_type="schema",
        field_path="request.pii_count",
        value=500000,
        normalized_value=500000,
        evidence_status="user_claim_only",
        can_support_external_positive_claim=False,
    )
    pack = GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[fact],
        diagnosis_result={},
        regulations=[],
        issues=[],
    )
    report = "企业出境个人信息约500000人，需进一步补充统计口径说明和核算依据。"
    issues = check_user_claim_positive_statement(report, pack)
    assert issues == []
