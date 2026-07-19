from backend.common.workflow import GenerationContextPack, IssueItem
from backend.domains.cn.security_assessment.consistency_checker import check_internal_expression_leakage
from backend.domains.cn.security_assessment.writing_strategy_builder import build_writing_strategy


def _context_pack(issues: list[IssueItem]) -> GenerationContextPack:
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


def test_external_expressions_do_not_leak_internal_content() -> None:
    """All external_expressions should not contain internal_expression fragments."""
    high_issues = [
        IssueItem(
            issue_id="ISSUE-recipient-security-evidence-missing",
            title="境外接收方安全保障能力证明不足",
            description="当前材料对境外接收方安全能力描述不足。",
            category="recipient",
            severity="HIGH",
            fact_refs=[],
            recommended_action="补充境外接收方安全管理制度和认证证明。",
            affects_outputs=["recipient_capability"],
        ),
        IssueItem(
            issue_id="ISSUE-consent-evidence-missing",
            title="个人信息出境单独同意记录证据不足",
            description="涉及个人信息出境时未验证是否已取得单独同意。",
            category="consent",
            severity="HIGH",
            fact_refs=[],
            recommended_action="补充告知和单独同意记录。",
            affects_outputs=["necessity_legal_basis"],
        ),
        IssueItem(
            issue_id="ISSUE-legal-document-gaps",
            title="法律文件核心条款可能存在缺失",
            description="与境外接收方签署的法律文件未验证核心条款。",
            category="legal_document",
            severity="HIGH",
            fact_refs=[],
            recommended_action="核验法律文件是否覆盖六项核心条款。",
            affects_outputs=["recipient_capability"],
        ),
    ]
    pack = _context_pack(high_issues)
    strategies = pack.writing_strategy["strategies"]

    for strategy in strategies:
        external = strategy.get("external_expression", "")
        # The external expression by itself should have no internal leaks
        leaked = check_internal_expression_leakage(external, pack)
        assert leaked == [], f"{strategy['issue_id']}: external expression triggered leak detection: {leaked}"


def test_all_high_severity_issues_have_conservative_tone() -> None:
    """HIGH and BLOCKER issues should get conservative tone."""
    issues = [
        IssueItem(
            issue_id="ISSUE-ciio-security-assessment",
            title="CIIO 触发安全评估路径",
            description="输入事实显示企业属于 CIIO。",
            category="path",
            severity="HIGH",
            fact_refs=["FACT-request-is_ciio"],
            recommended_action="按安全评估申报要求准备材料。",
            affects_outputs=["overview"],
        ),
        IssueItem(
            issue_id="ISSUE-necessity-argument-generic",
            title="出境必要性论证可能过于泛化",
            description="当前出境目的描述可能不足以支撑必要性审查。",
            category="necessity",
            severity="MEDIUM",
            fact_refs=[],
            recommended_action="补充业务必要性论证。",
            affects_outputs=["necessity_legal_basis"],
        ),
    ]
    pack = _context_pack(issues)
    strategies = pack.writing_strategy["strategies"]
    by_id = {s["issue_id"]: s for s in strategies}

    assert by_id["ISSUE-ciio-security-assessment"]["tone"] == "conservative"
    assert by_id["ISSUE-necessity-argument-generic"]["tone"] == "balanced"
