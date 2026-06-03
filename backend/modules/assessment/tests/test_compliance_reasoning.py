"""Test compliance reasoning, citation quality, and agent modules."""

from backend.common.workflow.facts import FactItem
from backend.common.workflow.issues import IssueItem
from backend.modules.assessment.compliance_reasoning import (
    ComplianceReasoningItem,
    build_compliance_reasoning,
    render_compliance_reasoning_markdown,
)
from backend.modules.assessment.citation_quality import (
    validate_citation_for_issue,
    validate_all_citations,
    CitationValidation,
)
from backend.modules.assessment.agents.input_normalization import InputNormalizationAgent
from backend.modules.assessment.agents.data_classification import DataClassificationAgent
from backend.modules.assessment.agents.expression_calibration import ExpressionCalibrationAgent


def test_compliance_reasoning_all_targets():
    """Verify reasoning items cover all core targets."""
    facts = [
        FactItem(fact_id="F-1", source_type="schema", source_ref="test",
                 field_path="company_name", value="TestCo", normalized_value="TestCo",
                 confidence=0.6, evidence_status="user_claim_only", can_support_external_positive_claim=False),
    ]
    issues = [
        IssueItem(issue_id="I-1", title="Missing consent", description="...",
                  category="consent", severity="HIGH", fact_refs=["F-1"],
                  rule_refs=[], recommended_action="...", affects_outputs=["data_scope"]),
    ]
    items = build_compliance_reasoning(facts, issues)

    assert len(items) >= 6  # Should cover most core targets
    targets = {item.target for item in items}
    assert "境外接收方安全保障能力" in targets
    assert "个人信息出境告知同意" in targets


def test_compliance_reasoning_markdown():
    """Verify markdown rendering works."""
    items = [ComplianceReasoningItem(
        target="测试维度",
        user_claim="用户声称X",
        fact_status="user_claim_only",
        reasonableness="方向合理但缺少证据",
        ambiguity="未提供证明材料",
        legal_risk="可能不满足要求",
        possible_non_compliance="无法证明合规",
        correct_expression="应表述为待补充",
        external_claim_allowed=False,
    )]
    md = render_compliance_reasoning_markdown(items)
    assert "测试维度" in md
    assert "user_claim_only" in md
    assert "不可正面肯定" in md


def test_citation_quality_exact_support():
    """Verify exact support detection for consent issues."""
    level = validate_citation_for_issue(
        "TEST-1", "consent",
        "个人信息保护法", "第三十九条"
    )
    assert level == "exact_support"


def test_citation_quality_partial_support():
    """Verify partial support detection."""
    level = validate_citation_for_issue(
        "TEST-2", "legal_document",
        "个人信息保护法", "第三十八条"
    )
    assert level == "partial_support"


def test_citation_quality_irrelevant():
    """Verify irrelevant citation detection."""
    level = validate_citation_for_issue(
        "TEST-3", "consent",
        "Some Random US Law", "Section 123"
    )
    assert level == "irrelevant"


def test_citation_quality_background():
    """Verify background-only detection."""
    level = validate_citation_for_issue(
        "TEST-4", "recipient",
        "网络安全法", "第二十一条"
    )
    assert level == "background_only"


def test_input_normalization_agent():
    """Verify input normalization identifies missing fields."""
    agent = InputNormalizationAgent()
    result = agent.run({"company_name": "TestCo", "industry": "Tech"})
    assert len(result.field_statuses) > 0
    missing = [fs.field_path for fs in result.field_statuses if fs.status == "missing"]
    assert len(missing) > 0  # Should have missing fields


def test_data_classification_agent():
    """Verify data classification identifies SPI indicators."""
    agent = DataClassificationAgent()
    items = [
        {"name": "健康数据", "description": "patient health records", "volume": "10000"},
        {"name": "邮箱地址", "description": "customer email", "volume": "50000"},
    ]
    results = agent.run(items)
    assert len(results) == 2
    # Health data should be flagged as SPI candidate
    assert results[0].sensitive_personal_information_candidate is True
    # Email should be flagged as PII
    assert results[1].personal_information_candidate is True


def test_expression_calibration_detects_over_commitment():
    """Verify calibration detects over-commitment in external reports."""
    agent = ExpressionCalibrationAgent()
    report = "该公司已完全建立数据安全保障体系，不存在任何合规风险，材料齐全，可以直接申报。"
    result = agent.run(report)
    assert len(result.changes) > 0
    assert not result.passed


def test_expression_calibration_passes_clean_report():
    """Verify calibration passes a properly-worded report."""
    agent = ExpressionCalibrationAgent()
    report = "用户已提供相关材料，建议在补充完善后提交申报。"
    result = agent.run(report)
    assert result.passed


def test_schema_extended_fields_parse():
    """Verify new extended AssessmentRequest fields parse correctly."""
    from backend.modules.assessment.schema import (
        AssessmentRequest, DataInventoryItem, RecipientInfo, LegalDocumentReview,
    )

    payload = AssessmentRequest.model_validate({
        "company_name": "测试企业",
        "industry": "金融",
        "transfer_purpose": "风险监控",
        "receiver_country": "香港",
        "data_inventory_items": [
            {"name": "客户资产汇总", "description": "资产总额", "data_subject": "高净值客户",
             "personal_info_type": "sensitive_personal_information", "is_important_data_candidate": True}
        ],
        "recipient_info": {
            "name": "东方金融控股集团", "country_or_region": "香港",
            "role": "境外接收方", "relationship": "母公司"
        },
        "legal_document_review": {
            "document_name": "集团数据处理协议",
            "clause_coverage": {"purpose_method_scope": "covered"},
            "risk_level": "MEDIUM"
        },
    })

    assert len(payload.data_inventory_items) == 1
    assert payload.data_inventory_items[0].name == "客户资产汇总"
    assert payload.recipient_info is not None
    assert payload.recipient_info.name == "东方金融控股集团"
    assert payload.legal_document_review is not None
    assert payload.legal_document_review.document_name == "集团数据处理协议"
