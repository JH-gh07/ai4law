from backend.modules.assessment.consistency_checker import (
    check_forbidden_expressions,
    check_internal_expression_leakage,
)
from backend.modules.assessment.writing_strategy_builder import build_writing_strategy
from backend.common.workflow import GenerationContextPack, IssueItem


def _context_pack_with_strategy(issues: list[IssueItem]) -> GenerationContextPack:
    ws = build_writing_strategy(issues)
    return GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[],
        diagnosis_result={},
        regulations=[],
        issues=issues,
        writing_strategy=ws,
    )


def test_forbidden_expression_detected_in_report() -> None:
    issue = IssueItem(
        issue_id="ISSUE-recipient-security-evidence-missing",
        title="境外接收方安全保障能力证明不足",
        description="当前材料对境外接收方安全能力描述不足。",
        category="recipient",
        severity="HIGH",
        fact_refs=[],
        recommended_action="补充境外接收方安全管理制度和认证证明。",
        affects_outputs=["recipient_capability"],
    )
    pack = _context_pack_with_strategy([issue])
    report = "接收方具备充分安全保障能力，数据处理符合标准。"
    issues = check_forbidden_expressions(report, pack)
    assert any("接收方具备充分安全保障能力" in i for i in issues)


def test_report_without_forbidden_expressions_passes() -> None:
    issue = IssueItem(
        issue_id="ISSUE-recipient-security-evidence-missing",
        title="境外接收方安全保障能力证明不足",
        description="当前材料对境外接收方安全能力描述不足。",
        category="recipient",
        severity="HIGH",
        fact_refs=[],
        recommended_action="补充境外接收方安全管理制度和认证证明。",
        affects_outputs=["recipient_capability"],
    )
    pack = _context_pack_with_strategy([issue])
    report = "建议进一步补充境外接收方安全保障证明材料，以增强论证充分性。"
    issues = check_forbidden_expressions(report, pack)
    assert issues == []


def test_internal_expression_leakage_detected() -> None:
    issue = IssueItem(
        issue_id="ISSUE-consent-evidence-missing",
        title="个人信息出境单独同意记录证据不足",
        description="涉及个人信息出境时未验证是否已取得单独同意。",
        category="consent",
        severity="HIGH",
        fact_refs=[],
        recommended_action="补充告知和单独同意记录。",
        affects_outputs=["necessity_legal_basis"],
    )
    pack = _context_pack_with_strategy([issue])
    strategy = pack.writing_strategy["strategies"][0]
    internal_text = strategy["internal_expression"]
    # Extract a meaningful sentence from the internal expression
    sentence = internal_text.split("：")[-1].strip() if "：" in internal_text else internal_text
    if len(sentence) >= 15:
        report = f"综合来看，{sentence}"
        issues = check_internal_expression_leakage(report, pack)
        assert len(issues) >= 1


def test_internal_expression_not_in_clean_report() -> None:
    issue = IssueItem(
        issue_id="ISSUE-consent-evidence-missing",
        title="个人信息出境单独同意记录证据不足",
        description="涉及个人信息出境时未验证是否已取得单独同意。",
        category="consent",
        severity="HIGH",
        fact_refs=[],
        recommended_action="补充告知和单独同意记录。",
        affects_outputs=["necessity_legal_basis"],
    )
    pack = _context_pack_with_strategy([issue])
    strategy = pack.writing_strategy["strategies"][0]
    external_text = strategy["external_expression"]
    issues = check_internal_expression_leakage(external_text, pack)
    # Clean external expression should not contain internal text leaks
    assert issues == []


def test_global_forbidden_expressions_detected() -> None:
    issue = IssueItem(
        issue_id="ISSUE-missing-attachments",
        title="申报支撑材料缺失",
        description="当前请求未提供上传附件。",
        category="documentation",
        severity="MEDIUM",
        fact_refs=["FACT-request-uploaded_files"],
        recommended_action="补充材料。",
        affects_outputs=["risk_remediation"],
    )
    pack = _context_pack_with_strategy([issue])
    report = "经过评估，企业数据出境活动完全合规，无风险，材料齐备。"
    issues = check_forbidden_expressions(report, pack)
    # Should detect "完全合规", "无风险", "材料齐备"
    assert len(issues) >= 3
