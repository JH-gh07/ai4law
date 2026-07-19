from backend.common.workflow import EvidenceItem, FactItem, GenerationContextPack, IssueItem
from backend.domains.cn.security_assessment.consistency_checker import (
    check_context_pack_consistency,
    check_report_against_context,
)


def _pack(issue: IssueItem | None = None, evidence: EvidenceItem | None = None) -> GenerationContextPack:
    fact = FactItem(
        fact_id="FACT-request-is_ciio",
        source_type="schema",
        field_path="request.is_ciio",
        value=True,
        normalized_value=True,
    )
    material_fact = FactItem(
        fact_id="FACT-request-uploaded_files",
        source_type="schema",
        field_path="request.uploaded_files",
        value=[],
        normalized_value=[],
    )
    default_issue = IssueItem(
        issue_id="ISSUE-ciio-security-assessment",
        title="CIIO 触发安全评估路径",
        description="输入事实显示企业属于 CIIO。",
        category="path",
        severity="HIGH",
        fact_refs=[fact.fact_id],
        rule_refs=["diagnosis:ciio", "reg-pipl-40"],
        evidence_refs=["EVIDENCE-ciio-security-assessment"] if evidence else [],
        recommended_action="按安全评估申报要求准备材料。",
        affects_outputs=["overview"],
    )
    return GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[fact, material_fact],
        diagnosis_result={"recommended_path": "security_assessment"},
        regulations=[
            {
                "source_id": "reg-pipl-40",
                "title": "个人信息保护法",
                "article": "第40条",
                "snippet": "CIIO 个人信息出境相关要求。",
            }
        ],
        issues=[issue or default_issue],
        evidence_chain=[evidence] if evidence else [],
    )


def test_context_pack_consistency_detects_missing_fact_ref() -> None:
    issue = IssueItem(
        issue_id="ISSUE-broken",
        title="坏引用",
        description="构造缺失 fact_ref。",
        category="path",
        severity="HIGH",
        fact_refs=["FACT-missing"],
        rule_refs=["reg-pipl-40"],
        recommended_action="修复引用。",
        affects_outputs=["overview"],
    )

    issues = check_context_pack_consistency(_pack(issue=issue))

    assert any("FACT-missing" in item for item in issues)


def test_context_pack_consistency_detects_missing_evidence_rule_ref() -> None:
    evidence = EvidenceItem(
        evidence_id="EVIDENCE-ciio-security-assessment",
        claim="CIIO 事实触发安全评估路径判断",
        fact_refs=["FACT-request-is_ciio"],
        rule_refs=["reg-missing"],
        conclusion="应按安全评估路径准备材料。",
        confidence=0.9,
        used_by=["ISSUE-ciio-security-assessment"],
    )

    issues = check_context_pack_consistency(_pack(evidence=evidence))

    assert any("reg-missing" in item for item in issues)


def test_report_against_context_detects_missing_high_issue() -> None:
    issues = check_report_against_context("报告只写了一般背景。", _pack())

    assert any("ISSUE-ciio-security-assessment" in item for item in issues)


def test_report_against_context_detects_material_completion_conflict() -> None:
    issue = IssueItem(
        issue_id="ISSUE-missing-attachments",
        title="申报支撑材料缺失",
        description="当前请求未提供上传附件。",
        category="documentation",
        severity="MEDIUM",
        fact_refs=["FACT-request-uploaded_files"],
        recommended_action="需补充数据清单、隐私政策和合同材料。",
        affects_outputs=["risk_remediation"],
    )

    issues = check_report_against_context("经审查，材料齐备。", _pack(issue=issue))

    assert any("materials are complete" in item for item in issues)


def test_report_against_context_detects_missing_path_warning_statement() -> None:
    pack = _pack()
    pack.path_warning = "诊断推荐路径为 scc_or_certification，当前为强制生成安全评估报告。"
    pack.diagnosis_result = {"recommended_path": "scc_or_certification"}

    issues = check_report_against_context("报告只写了一般结论。", pack)

    assert any("path warning" in item for item in issues)
    assert any("forced-generation" in item for item in issues)


def test_report_against_context_detects_unknown_important_data_denial() -> None:
    pack = _pack()
    pack.facts.append(
        FactItem(
            fact_id="FACT-request-contains_important_data",
            source_type="schema",
            field_path="request.contains_important_data",
            value="unknown",
            normalized_value="unknown",
        )
    )

    issues = check_report_against_context("经确认，本项目不涉及重要数据。", pack)

    assert any("important data" in item for item in issues)
