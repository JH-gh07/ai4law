import pytest
from pydantic import ValidationError

from backend.common.workflow import EvidenceItem, FactItem, GenerationContextPack, IssueItem


def test_fact_item_requires_stable_id() -> None:
    with pytest.raises(ValidationError):
        FactItem(source_type="schema", value="x")


def test_issue_item_validates_category_and_severity() -> None:
    with pytest.raises(ValidationError):
        IssueItem(
            issue_id="ISSUE-1",
            title="bad",
            description="bad",
            category="invalid",
            severity="HIGH",
            fact_refs=["FACT-1"],
            recommended_action="fix",
        )

    with pytest.raises(ValidationError):
        IssueItem(
            issue_id="ISSUE-1",
            title="bad",
            description="bad",
            category="path",
            severity="CRITICAL",
            fact_refs=["FACT-1"],
            recommended_action="fix",
        )


def test_issue_item_accepts_personal_information_rights_protection() -> None:
    issue = IssueItem(
        issue_id="ISSUE-rights-channel",
        title="个人信息行权机制不完善",
        description="数据主体权利行使渠道缺少可操作信息。",
        category="rights_protection",
        severity="MEDIUM",
        fact_refs=["FACT-request-dsar"],
        recommended_action="补充受理渠道和响应时限。",
    )

    assert issue.category == "rights_protection"


def test_context_pack_json_serializes() -> None:
    fact = FactItem(
        fact_id="FACT-request-company_name",
        source_type="schema",
        field_path="request.company_name",
        value="测试公司",
    )
    issue = IssueItem(
        issue_id="ISSUE-path-mismatch",
        title="路径不匹配",
        description="诊断路径与当前报告类型不一致。",
        category="path",
        severity="HIGH",
        fact_refs=[fact.fact_id],
        recommended_action="复核路径。",
    )
    evidence = EvidenceItem(
        evidence_id="EVIDENCE-path",
        claim="建议走安全评估路径",
        fact_refs=[fact.fact_id],
        rule_refs=["diagnosis:ciio"],
        conclusion="需要安全评估。",
        confidence=0.9,
    )

    pack = GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[fact],
        diagnosis_result={"recommended_path": "security_assessment"},
        regulations=[],
        issues=[issue],
        evidence_chain=[evidence],
    )

    assert "FACT-request-company_name" in pack.model_dump_json()
