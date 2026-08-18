"""task081 T081-02 — 结构化输入与附件证据合并测试。

验证：
1. 结构化认证（ISO27001）区分"已声明认证"与"缺少证书"，不写成完全无认证。
2. `legal_environment_change_response=missing` 进入具体 Issue ID。
3. 非空 data_inventory_items / recipient_info 不被整体标记为未提供。
4. missing_materials 输出具体键值（非全空）。
5. Minimal 仍保留附件缺失；Structured 不因无上传附件抹掉结构化证据。
"""
from __future__ import annotations

from backend.domains.cn.security_assessment.fact_builder import build_assessment_facts
from backend.domains.cn.security_assessment.issue_builder import build_assessment_issues
from backend.domains.cn.security_assessment.profile_extractor import ProfileExtractor
from backend.domains.cn.security_assessment.schema import AssessmentRequest, RegulationHit
from backend.domains.cn.transfer_diagnosis.schema import DiagnosisResult


def _diagnosis(path: str = "security_assessment") -> DiagnosisResult:
    return DiagnosisResult(
        recommended_path=path,
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


def _build(request: AssessmentRequest) -> dict[str, object]:
    diagnosis = _diagnosis()
    profile = ProfileExtractor().extract(request)
    facts = build_assessment_facts(request, profile, diagnosis)
    issues = build_assessment_issues(facts, diagnosis, _regulations(), [])
    return {issue.issue_id: issue for issue in issues}


def _structured_request() -> AssessmentRequest:
    return AssessmentRequest(
        company_name="跨境优品科技有限公司",
        industry="跨境电商",
        is_ciio=False,
        contains_important_data=False,
        pii_count=450000,
        spi_count=0,
        transfer_purpose="订单数据同步至新加坡",
        receiver_country="新加坡",
        uploaded_files=[],
        data_inventory_items=[
            {"name": "用户姓名", "personal_info_type": "personal_information"},
            {"name": "收货地址", "personal_info_type": "personal_information"},
        ],
        recipient_info={
            "name": "SeaCommerce Pte. Ltd.",
            "country_or_region": "新加坡",
            "role": "境外接收方",
        },
        legal_document_review={
            "document_name": "数据跨境处理协议",
            "clause_coverage": {
                "purpose_method_scope": "covered",
                "overseas_retention_location_period": "covered",
                "onward_transfer_constraint": "covered",
                "legal_environment_change_response": "missing",
                "breach_liability_dispute_resolution": "covered",
                "incident_response_and_individual_rights": "partial",
            },
            "missing_items": ["法律环境变化应对条款"],
        },
        security_capability={
            "management_measures": ["数据安全管理制度"],
            "technical_measures": ["加密传输"],
            "certifications": ["ISO27001"],
        },
        system_link={
            "domestic_systems": ["杭州阿里云RDS数据库"],
            "transfer_links": ["加密API同步"],
            "overseas_systems": ["新加坡AWS Redshift"],
        },
    )


def test_structured_certification_distinguishes_declared_vs_evidence() -> None:
    by_id = _build(_structured_request())

    # 已声明 ISO27001 → 不得写"完全无认证"，应细化为"缺证书佐证"
    assert "ISSUE-recipient-security-evidence-missing" not in by_id
    cert_issue = by_id["ISSUE-recipient-certification-evidence-missing"]
    assert "ISO27001" in cert_issue.description
    assert "已声明认证" in cert_issue.title
    assert cert_issue.severity == "MEDIUM"
    assert any("证书佐证" in m for m in cert_issue.missing_materials)


def test_structured_legal_environment_change_missing_has_dedicated_issue() -> None:
    by_id = _build(_structured_request())

    clause_issue = by_id["ISSUE-legal-document-clause-missing-legal_environment_change_response"]
    assert "法律环境变化应对条款" in clause_issue.title
    assert "legal_document_review.clause_coverage.legal_environment_change_response" in (
        clause_issue.missing_materials
    )


def test_structured_data_inventory_not_marked_entirely_missing() -> None:
    by_id = _build(_structured_request())

    # 非空 data_inventory_items → material-checklist 不应再把"数据清单"列为缺失
    checklist = by_id["ISSUE-material-checklist-incomplete"]
    assert not any(m == "数据清单" for m in checklist.missing_materials)


def test_structured_missing_materials_not_all_empty() -> None:
    issues = list(_build(_structured_request()).values())
    non_empty = [issue for issue in issues if issue.missing_materials]
    assert len(non_empty) >= 3
    # 关键材料类 Issue 必须有具体键值
    for key in (
        "ISSUE-consent-evidence-missing",
        "ISSUE-onward-transfer-unclear",
        "ISSUE-material-checklist-incomplete",
    ):
        assert issues and key in {i.issue_id for i in issues}


def test_minimal_keeps_attachment_missing_and_no_declared_cert() -> None:
    request = AssessmentRequest(
        company_name="云帆数据科技有限公司",
        industry="互联网SaaS",
        is_ciio=False,
        contains_important_data=False,
        pii_count=1200000,
        spi_count=15000,
        transfer_purpose="全球客服与风控联防",
        receiver_country="新加坡",
        uploaded_files=[],
    )
    by_id = _build(request)

    # Minimal 仍保留附件缺失
    assert "ISSUE-missing-attachments" in by_id
    # 无结构化认证 → 输出"完全无认证信息"，而非"已声明认证"
    assert "ISSUE-recipient-security-evidence-missing" in by_id
    assert "ISSUE-recipient-certification-evidence-missing" not in by_id


def test_structured_keeps_attachment_missing_but_preserves_structured_evidence() -> None:
    by_id = _build(_structured_request())

    # 无上传附件仍保留附件缺失
    assert "ISSUE-missing-attachments" in by_id
    # 但结构化认证/条款证据不被抹掉
    assert "ISSUE-recipient-certification-evidence-missing" in by_id
    assert "ISSUE-legal-document-clause-missing-legal_environment_change_response" in by_id
