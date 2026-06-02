"""Test DPIA service with the new DPIARequest schema (without LLM)."""

from unittest.mock import MagicMock, patch

from backend.modules.dpia.schema import DPIARequest, DPIAResult
from backend.modules.dpia.service import DPIAService


_VALID_PAYLOAD = {
    "project_name": "员工健康评估系统",
    "project_goal": "通过AI算法对员工健康数据进行评估和分类",
    "dpia_trigger_reasons": ["处理特殊类别个人数据", "自动化决策"],
    "processing_flow_description": "收集员工体检报告和可穿戴设备健康数据，进行健康风险评分",
    "data_categories": ["体检数据", "心率", "睡眠数据"],
    "special_category_data": True,
    "special_category_types": ["健康数据"],
    "data_subject_categories": ["员工"],
    "data_subject_count": "5,000人",
    "retention_period": "在职期间及离职后3年",
    "cross_border_transfer": True,
    "transfer_destination": "United States",
    "automated_decision_making": True,
    "large_scale_processing": False,
    "data_matching": False,
    "new_technology": True,
    "vulnerable_data_subjects": True,
    "consulted_internal_departments": ["法务部", "HR部门"],
    "external_experts": ["数据保护律师事务所"],
    "data_subject_consultation_plan": "通过员工代表座谈会征询意见",
    "lawful_basis": ["GDPR Art 6(1)(b)", "GDPR Art 9(2)(h)"],
    "necessity_statement": "处理员工健康数据是实现法定职业健康管理所必需，且无法以传统方式实现同等效率。",
    "proportionality_statement": "仅收集与职业健康评估直接相关的数据指标，限制处理频率为年度评估。",
    "transparency_information": "将通过员工隐私通知和入职文件告知处理详情。",
    "identified_risks": [
        {
            "risk_id": "RISK-001",
            "risk_description": "AI健康评分偏差导致歧视性评估",
            "likelihood": "medium",
            "impact": "high",
            "affected_data_subjects": "员工",
            "risk_source": "technology",
        }
    ],
    "mitigation_measures": [
        {
            "mitigation_id": "MIT-001",
            "description": "实施算法公平性审计",
            "target_risk_ids": ["RISK-001"],
            "status": "planned",
            "responsible_party": "数据科学团队",
        }
    ],
    "dpia_owner": "张经理",
    "dpo_name": "李律师",
    "dpo_opinion": "有待补充算法公平性验证报告",
    "review_date": "2026-06-03",
    "uploaded_files": ["flow.pdf", "privacy-policy.pdf"],
}


def test_dpia_request_parses() -> None:
    """Verify the new DPIARequest schema parses correctly."""
    req = DPIARequest.model_validate(_VALID_PAYLOAD)
    assert req.project_name == "员工健康评估系统"
    assert req.special_category_data is True
    assert req.automated_decision_making is True
    assert req.cross_border_transfer is True
    assert req.transfer_destination == "United States"
    assert len(req.identified_risks) == 1
    assert req.identified_risks[0].risk_id == "RISK-001"
    assert len(req.mitigation_measures) == 1
    assert req.mitigation_measures[0].mitigation_id == "MIT-001"
    assert req.dpo_name == "李律师"


def test_dpia_request_defaults() -> None:
    """Verify default values work correctly."""
    req = DPIARequest.model_validate({
        "project_name": "测试项目",
        "project_goal": "测试目的",
        "processing_flow_description": "测试处理流程",
    })
    assert req.special_category_data is False
    assert req.cross_border_transfer is False
    assert req.automated_decision_making is False
    assert req.systematic_monitoring is False
    assert req.large_scale_processing is False
    assert req.data_matching is False
    assert req.new_technology is False
    assert req.vulnerable_data_subjects is False
    assert req.identified_risks == []
    assert req.mitigation_measures == []
    assert req.lawful_basis == []


def test_dpia_need_detector_triggers() -> None:
    """Verify DPIANeedDetector evaluates WP248 triggers correctly."""
    from backend.modules.dpia.need_detector import DPIANeedDetector

    # High-risk: automated decision + special category + cross border
    req = DPIARequest.model_validate(_VALID_PAYLOAD)
    result = DPIANeedDetector.evaluate(req)
    assert result.dpia_required is True
    assert len(result.trigger_reasons) >= 3
    assert result.prior_consultation_possible is True
    assert "GDPR Article 35" in result.legal_basis or any(
        "GDPR Article 35" in b for b in result.legal_basis
    )

    # Low-risk: no triggers
    low_risk = DPIARequest.model_validate({
        "project_name": "低风险项目",
        "project_goal": "简单数据记录",
        "processing_flow_description": "记录日志用于运维",
    })
    result_low = DPIANeedDetector.evaluate(low_risk)
    assert result_low.dpia_required is False
    assert result_low.prior_consultation_possible is False


def test_fact_builder_produces_expected_facts() -> None:
    """Verify fact builder creates facts from request fields."""
    from backend.modules.dpia.fact_builder import build_dpia_facts
    from backend.modules.dpia.profile_extractor import DPIAProfileExtractor

    req = DPIARequest.model_validate(_VALID_PAYLOAD)
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)

    # Without diagnosis result
    facts = build_dpia_facts(request=req, profile=profile)
    fact_ids = {f.fact_id for f in facts}
    assert "DPIA-FACT-dpia-project-name" in fact_ids
    assert "DPIA-FACT-dpia-special-category-data" in fact_ids
    assert "DPIA-FACT-dpia-automated-decision-making" in fact_ids
    assert "DPIA-FACT-dpia-cross-border-transfer" in fact_ids

    # Schema facts should have confidence 0.6
    schema_facts = [f for f in facts if f.source_type == "schema"]
    for f in schema_facts:
        assert f.evidence_status == "user_claim_only"

    # With diagnosis result
    from backend.modules.dpia.need_detector import DPIANeedDetector
    diagnosis = DPIANeedDetector.evaluate(req)
    facts_with_diag = build_dpia_facts(request=req, profile=profile, diagnosis_result=diagnosis)
    diag_fact_ids = {f.fact_id for f in facts_with_diag}
    assert "DPIA-FACT-dpia-need-dpia-required" in diag_fact_ids
    assert "DPIA-FACT-dpia-need-prior-consultation-possible" in diag_fact_ids


def test_issue_builder_identifies_expected_issues() -> None:
    """Verify issue builder creates issues for triggering conditions."""
    from backend.modules.dpia.fact_builder import build_dpia_facts
    from backend.modules.dpia.issue_builder import build_dpia_issues
    from backend.modules.dpia.need_detector import DPIANeedDetector
    from backend.modules.dpia.profile_extractor import DPIAProfileExtractor

    req = DPIARequest.model_validate(_VALID_PAYLOAD)
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)
    diagnosis = DPIANeedDetector.evaluate(req)
    facts = build_dpia_facts(request=req, profile=profile, diagnosis_result=diagnosis)

    issues = build_dpia_issues(
        facts=facts,
        diagnosis_result=diagnosis,
        regulations=[],
        attachment_notes=[],
    )
    issue_ids = {i.issue_id for i in issues}

    assert "DPIA-ISSUE-automated-decision" in issue_ids
    assert "DPIA-ISSUE-special-category" in issue_ids
    assert "DPIA-ISSUE-new-technology" in issue_ids
    assert "DPIA-ISSUE-vulnerable-subjects" in issue_ids
    assert "DPIA-ISSUE-cross-border-risk" in issue_ids
    assert "DPIA-ISSUE-prior-consultation-needed" in issue_ids


def test_evidence_builder_links_issues_to_facts() -> None:
    """Verify evidence builder creates well-formed evidence items."""
    from backend.modules.dpia.evidence_builder import build_dpia_evidence
    from backend.modules.dpia.fact_builder import build_dpia_facts
    from backend.modules.dpia.issue_builder import build_dpia_issues
    from backend.modules.dpia.need_detector import DPIANeedDetector
    from backend.modules.dpia.profile_extractor import DPIAProfileExtractor

    req = DPIARequest.model_validate(_VALID_PAYLOAD)
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)
    diagnosis = DPIANeedDetector.evaluate(req)
    facts = build_dpia_facts(request=req, profile=profile, diagnosis_result=diagnosis)
    issues = build_dpia_issues(facts=facts, diagnosis_result=diagnosis, regulations=[], attachment_notes=[])

    updated_issues, evidence_chain = build_dpia_evidence(
        facts=facts, issues=issues, regulations=[]
    )
    assert len(evidence_chain) > 0
    for ev in evidence_chain:
        assert ev.evidence_id.startswith("DPIA-EVIDENCE-")
        assert ev.claim
        assert ev.conclusion
        assert 0 <= ev.confidence <= 1.0


def test_writing_strategy_forbids_correct_expressions() -> None:
    """Verify DPIA-specific forbidden expressions are included."""
    from backend.modules.dpia.writing_strategy_builder import build_writing_strategy
    from backend.common.workflow import IssueItem

    issue = IssueItem(
        issue_id="DPIA-ISSUE-automated-decision",
        title="自动化决策",
        description="涉及自动化决策",
        category="automated_decision",
        severity="HIGH",
        fact_refs=["F-1"],
        rule_refs=["GDPR Art 22"],
        recommended_action="补充人工干预机制",
        affects_outputs=["risk_assessment"],
    )
    strategy = build_writing_strategy([issue])
    global_forbidden = strategy["global_forbidden_expressions"]
    assert "风险已完全消除" in global_forbidden
    assert "可直接上线" in global_forbidden
    assert "不存在歧视风险" in global_forbidden
    assert len(strategy["strategies"]) == 1


def test_legal_grounding_returns_expected_structure() -> None:
    """Verify DPIA legal grounding produces correctly structured output."""
    from backend.modules.dpia.legal_grounding import build_dpia_legal_grounding
    from backend.common.workflow import IssueItem, FactItem
    from backend.modules.dpia.schema import RegulationHit

    facts = [
        FactItem(
            fact_id="F-1", source_type="schema", source_ref="test",
            field_path="dpia.automated_decision_making",
            value=True, normalized_value=True, confidence=0.6,
            evidence_status="user_claim_only",
            can_support_external_positive_claim=False,
        )
    ]
    issues = [
        IssueItem(
            issue_id="DPIA-ISSUE-automated-decision",
            title="自动化决策",
            description="涉及自动化决策",
            category="automated_decision",
            severity="HIGH",
            fact_refs=["F-1"],
            rule_refs=["GDPR Article 22"],
            recommended_action="补充人工干预",
            affects_outputs=["risk_assessment"],
        )
    ]
    regulations = [
        RegulationHit(
            source_id="reg-001",
            title="GDPR",
            article="Article 22",
            snippet="Automated individual decision-making safeguards.",
        )
    ]

    legal, case = build_dpia_legal_grounding(
        issues=issues, facts=facts, regulations=regulations
    )
    assert legal["grounding_version"] == "dpia-v1"
    assert "DPIA-ISSUE-automated-decision" in legal["by_issue"]
    assert len(legal["by_issue"]["DPIA-ISSUE-automated-decision"]) > 0


def test_consistency_checker_detects_missing_citations() -> None:
    """Verify consistency checker detects chapters without citations."""
    from backend.modules.dpia.consistency_checker import DPIAConsistencyChecker
    from backend.modules.dpia.schema import DPIAChapterContent, DPIAProjectProfile

    profile = DPIAProjectProfile(
        project_name="测试",
        project_goal="测试",
        processing_flow_description="测试",
        data_categories=[],
        special_category_data=False,
        special_category_types=[],
        data_subject_categories=[],
        data_subject_count="",
        retention_period="",
        cross_border_transfer=False,
        transfer_destination="",
        automated_decision_making=False,
        systematic_monitoring=False,
        large_scale_processing=False,
        data_matching=False,
        new_technology=False,
        vulnerable_data_subjects=False,
        lawful_basis=[],
        dpia_trigger_reasons=[],
    )
    chapters = [
        DPIAChapterContent(chapter_no=1, title="测试章节", content="内容", citations=[])
    ]
    checker = DPIAConsistencyChecker()
    issues = checker.check(profile, chapters)
    assert any("no citations" in i.lower() for i in issues)


def test_profile_extractor_handles_uploaded_files() -> None:
    """Verify profile extractor correctly handles uploaded files."""
    from backend.modules.dpia.profile_extractor import DPIAProfileExtractor

    req = DPIARequest.model_validate(_VALID_PAYLOAD)
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)
    assert profile.project_name == req.project_name
    assert profile.special_category_data is True
    assert profile.automated_decision_making is True
    assert profile.cross_border_transfer is True


def test_noop_validate_returns_none() -> None:
    """Verify DPIA no-op validate always returns None."""
    result = DPIAService._noop_validate(None, "", "")
    assert result is None


def test_noop_check_alignment_returns_empty() -> None:
    """Verify DPIA no-op alignment check returns empty list."""
    result = DPIAService._noop_check_alignment("report content", None)
    assert result == []
