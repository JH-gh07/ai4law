from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.modules.assessment.generation_basis import build_generation_basis_pack
from backend.modules.assessment.legal_grounding import build_legal_grounding
from backend.modules.assessment.schema import RegulationHit
from backend.modules.assessment.writing_strategy_builder import build_writing_strategy


def test_generation_basis_pack_includes_issue_level_legal_grounding() -> None:
    facts = [
        FactItem(
            fact_id="FACT-recipient-security",
            source_type="schema",
            field_path="request.recipient_info.security_evidence",
            value="仅说明符合国际标准，未提供认证材料",
            normalized_value="仅说明符合国际标准，未提供认证材料",
        )
    ]
    issues = [
        IssueItem(
            issue_id="ISSUE-recipient-security-evidence-missing",
            title="境外接收方安全能力证明不足",
            description="境外接收方仅有概括性安全能力描述。",
            category="recipient",
            severity="HIGH",
            fact_refs=["FACT-recipient-security"],
            rule_refs=["reg-assessment-article5"],
            evidence_refs=["EV-recipient-security"],
            recommended_action="补充接收方认证、审计或安全制度材料。",
            affects_outputs=["recipient_capability"],
        )
    ]
    evidence_chain = [
        EvidenceItem(
            evidence_id="EV-recipient-security",
            claim="接收方安全能力证明不足",
            fact_refs=["FACT-recipient-security"],
            rule_refs=["reg-assessment-article5"],
            conclusion="需要补充证明材料。",
            confidence=0.8,
            used_by=["ISSUE-recipient-security-evidence-missing"],
        )
    ]
    regulations = [
        RegulationHit(
            source_id="reg-assessment-article5",
            title="数据出境安全评估办法",
            article="第五条",
            snippet="评估境外接收方安全保障能力以及所在国家或者地区的数据安全保护政策法规。",
        )
    ]

    grounding, _case_grounding = build_legal_grounding(issues=issues, facts=facts, regulations=regulations)
    pack = build_generation_basis_pack(
        task_id="task-1",
        facts=facts,
        issues=issues,
        evidence_chain=evidence_chain,
        regulations=regulations,
        attachment_notes=[],
        path_warning=None,
        legal_grounding=grounding,
    )

    section = next(item for item in pack["section_packs"] if item["section_id"] == "recipient_capability")
    assert pack["legal_grounding"]["by_issue"]["ISSUE-recipient-security-evidence-missing"]
    assert section["legal_grounding"][0]["rule_id"] == "reg-assessment-article5"
    assert section["legal_grounding"][0]["confidence_score"] >= 0.6
    assert "仅说明符合国际标准" in section["legal_grounding"][0]["query_context"]


def test_generation_basis_pack_maps_section_to_writing_strategy() -> None:
    facts = [
        FactItem(
            fact_id="FACT-consent",
            source_type="schema",
            field_path="request.consent_info.consent_evidence",
            value="未提供同意日志",
            normalized_value="未提供同意日志",
        )
    ]
    issues = [
        IssueItem(
            issue_id="ISSUE-consent-evidence-missing",
            title="个人信息告知同意或豁免依据证明不足",
            description="存在个人信息出境但未明确单独同意记录。",
            category="consent",
            severity="HIGH",
            fact_refs=["FACT-consent"],
            recommended_action="补充单独同意记录。",
            affects_outputs=["rights_impact"],
        )
    ]
    writing_strategy = build_writing_strategy(issues)

    pack = build_generation_basis_pack(
        task_id="task-1",
        facts=facts,
        issues=issues,
        evidence_chain=[],
        regulations=[],
        attachment_notes=[],
        path_warning=None,
        writing_strategy=writing_strategy,
    )

    section = next(item for item in pack["section_packs"] if item["section_id"] == "rights_impact")
    assert section["writing_strategy_refs"] == ["ISSUE-consent-evidence-missing"]
    assert section["writing_strategies"][0]["issue_id"] == "ISSUE-consent-evidence-missing"
    assert "单独同意" in section["writing_strategies"][0]["external_expression"]


def test_generation_basis_pack_separates_workflow_rules_from_regulations() -> None:
    pack = build_generation_basis_pack(
        task_id="task-2",
        facts=[],
        issues=[],
        evidence_chain=[],
        regulations=[],
        attachment_notes=[],
        path_warning=None,
        workflow_rules=[{"chunk_id": "WF-1", "title": "安全评估规则"}],
        template_context=[{"chunk_id": "TPL-1", "title": "正式模板"}],
    )
    assert pack["regulations"] == []
    assert pack["workflow_rules"] == [{"chunk_id": "WF-1", "title": "安全评估规则"}]
    assert pack["template_context"] == [{"chunk_id": "TPL-1", "title": "正式模板"}]
