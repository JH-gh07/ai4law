"""Test the active compliance reasoning and assessment schema."""

from backend.common.workflow.facts import FactItem
from backend.common.workflow.issues import IssueItem
from backend.domains.cn.security_assessment.compliance_reasoning import (
    ComplianceReasoningItem,
    build_compliance_reasoning,
    render_compliance_reasoning_markdown,
)


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


def test_schema_extended_fields_parse():
    """Verify new extended AssessmentRequest fields parse correctly."""
    from backend.domains.cn.security_assessment.schema import AssessmentRequest

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
