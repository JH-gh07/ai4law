from backend.common.workflow import FactItem, IssueItem
from backend.modules.assessment.legal_grounding import build_legal_grounding
from backend.modules.assessment.schema import RegulationHit


def test_legal_grounding_binds_issue_to_direct_rule_refs() -> None:
    issue = IssueItem(
        issue_id="ISSUE-legal-document-gaps",
        title="法律文件责任义务信息不足",
        description="缺少再转移约束和违约责任等核心条款。",
        category="contract",
        severity="HIGH",
        fact_refs=["FACT-contract"],
        rule_refs=["reg-assessment-article9"],
        recommended_action="补充法律文件核心条款。",
        affects_outputs=["security_measures"],
    )
    facts = [
        FactItem(
            fact_id="FACT-contract",
            source_type="schema",
            field_path="request.legal_document_info.key_terms_summary",
            value="缺少再转移约束",
            normalized_value="缺少再转移约束",
        )
    ]
    regulations = [
        RegulationHit(
            source_id="reg-assessment-article9",
            title="数据出境安全评估办法",
            article="第九条",
            snippet="法律文件应约定再转移约束、保存期限、违约责任和争议解决等内容。",
        )
    ]

    grounding = build_legal_grounding(issues=[issue], facts=facts, regulations=regulations)
    items = grounding["by_issue"]["ISSUE-legal-document-gaps"]

    assert items
    assert items[0]["rule_id"] == "reg-assessment-article9"
    assert items[0]["confidence_score"] >= 0.6
    assert "直接引用" in items[0]["relevance_reason"]
    assert items[0]["source_version"]


def test_legal_grounding_uses_issue_facts_in_query_context() -> None:
    issue = IssueItem(
        issue_id="ISSUE-consent-evidence-missing",
        title="个人信息告知同意或豁免依据证明不足",
        description="存在个人信息出境但未明确单独同意记录。",
        category="consent",
        severity="HIGH",
        fact_refs=["FACT-consent"],
        rule_refs=[],
        recommended_action="补充单独同意记录。",
        affects_outputs=["rights_impact"],
    )
    facts = [
        FactItem(
            fact_id="FACT-consent",
            source_type="schema",
            field_path="request.consent_info.consent_evidence",
            value="未提供同意日志",
            normalized_value="未提供同意日志",
        )
    ]
    regulations = [
        RegulationHit(
            source_id="reg-pipl-39",
            title="个人信息保护法",
            article="第三十九条",
            snippet="向境外提供个人信息应告知并取得个人的单独同意。",
        )
    ]

    grounding = build_legal_grounding(issues=[issue], facts=facts, regulations=regulations)
    items = grounding["by_issue"]["ISSUE-consent-evidence-missing"]

    assert items
    assert "未提供同意日志" in items[0]["query_context"]
    assert items[0]["confidence_score"] > 0
