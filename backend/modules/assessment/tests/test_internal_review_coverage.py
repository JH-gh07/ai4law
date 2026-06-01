from backend.common.workflow import IssueItem
from backend.modules.assessment.internal_review_generator import (
    build_internal_review_payload,
    generate_internal_review_markdown,
)
from backend.modules.assessment.writing_strategy_builder import build_writing_strategy


def _sample_generation_basis_pack() -> dict:
    return {
        "task_id": "test-task",
        "issues": [],
        "evidence_chain": [],
        "regulations": [],
        "legal_grounding": {"by_issue": {}},
    }


def test_internal_review_payload_covers_all_high_issues() -> None:
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
            issue_id="ISSUE-missing-attachments",
            title="申报支撑材料缺失",
            description="当前请求未提供上传附件。",
            category="documentation",
            severity="MEDIUM",
            fact_refs=["FACT-request-uploaded_files"],
            recommended_action="补充数据清单和合同材料。",
            affects_outputs=["risk_remediation"],
        ),
    ]
    ws = build_writing_strategy(issues)
    basis_pack = _sample_generation_basis_pack()
    basis_pack["issues"] = [issue.model_dump() for issue in issues]

    payload = build_internal_review_payload(
        issues=issues,
        writing_strategy=ws,
        generation_basis_pack=basis_pack,
        material_rows=[
            {"source_ref": "privacy_policy.pdf", "summary": "待补充", "status": "待补充"}
        ],
    )

    high_risk_issues = payload["high_risk_issues"]
    high_issue_ids = {issue["issue_id"] for issue in high_risk_issues}
    assert "ISSUE-ciio-security-assessment" in high_issue_ids
    assert "ISSUE-consent-evidence-missing" in high_issue_ids
    assert "ISSUE-missing-attachments" not in high_issue_ids  # MEDIUM


def test_internal_review_overall_risk_is_high_with_high_issues() -> None:
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
    ]
    ws = build_writing_strategy(issues)
    basis_pack = _sample_generation_basis_pack()

    payload = build_internal_review_payload(
        issues=issues,
        writing_strategy=ws,
        generation_basis_pack=basis_pack,
        material_rows=[],
    )

    assert payload["overall_risk"] == "HIGH"


def test_internal_review_overall_risk_is_low_without_issues() -> None:
    ws = build_writing_strategy([])
    basis_pack = _sample_generation_basis_pack()

    payload = build_internal_review_payload(
        issues=[],
        writing_strategy=ws,
        generation_basis_pack=basis_pack,
        material_rows=[],
    )

    assert payload["overall_risk"] == "LOW"


def test_internal_review_markdown_fallback_without_llm() -> None:
    """When LLM is None, generate_internal_review_markdown should produce fallback text."""
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
    ]
    ws = build_writing_strategy(issues)
    basis_pack = _sample_generation_basis_pack()

    payload = build_internal_review_payload(
        issues=issues,
        writing_strategy=ws,
        generation_basis_pack=basis_pack,
        material_rows=[],
    )

    markdown = generate_internal_review_markdown(payload=payload, llm_client=None)

    assert "内部 AI 检验文本" in markdown
    assert "总体风险判断" in markdown
    assert "CIIO" in markdown
    assert "高风险问题" in markdown
    assert "证据不足与材料补充" in markdown
    assert "正式文书中不宜直接出现的表述" in markdown
