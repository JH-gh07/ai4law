"""Test DPIA service — lower-level components + full 9-agent pipeline."""

from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from backend.domains.eu.dpia.schema import DPIARequest
from backend.domains.eu.dpia.service import DPIAService


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

# ── Helpers ──

def _make_service(use_llm: bool = False) -> DPIAService:
    if not use_llm:
        return DPIAService(llm_client=None)
    return DPIAService()


def _make_valid_request() -> DPIARequest:
    return DPIARequest.model_validate(_VALID_PAYLOAD)


# ── Schema tests ──

def test_dpia_request_parses() -> None:
    req = _make_valid_request()
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
    req = DPIARequest.model_validate({
        "project_name": "测试项目",
        "project_goal": "测试目的",
        "processing_flow_description": "测试处理流程",
    })
    assert req.special_category_data is False
    assert req.cross_border_transfer is False
    assert req.automated_decision_making is False
    assert req.identified_risks == []
    assert req.mitigation_measures == []


# ── Need detector tests ──

def test_dpia_need_detector_triggers() -> None:
    from backend.domains.eu.dpia.need_detector import DPIANeedDetector

    req = _make_valid_request()
    result = DPIANeedDetector.evaluate(req)
    assert result.dpia_required is True
    assert len(result.trigger_reasons) >= 3
    assert result.prior_consultation_possible is True

    low_risk = DPIARequest.model_validate({
        "project_name": "低风险项目", "project_goal": "简单数据记录",
        "processing_flow_description": "记录日志用于运维",
    })
    result_low = DPIANeedDetector.evaluate(low_risk)
    assert result_low.dpia_required is False
    assert result_low.prior_consultation_possible is False


# ── Fact builder tests ──

def test_fact_builder_produces_expected_facts() -> None:
    from backend.domains.eu.dpia.fact_builder import build_dpia_facts
    from backend.domains.eu.dpia.profile_extractor import DPIAProfileExtractor

    req = _make_valid_request()
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)
    facts = build_dpia_facts(request=req, profile=profile)
    fact_ids = {f.fact_id for f in facts}
    assert "DPIA-FACT-dpia-project-name" in fact_ids
    assert "DPIA-FACT-dpia-special-category-data" in fact_ids
    assert "DPIA-FACT-dpia-automated-decision-making" in fact_ids
    assert "DPIA-FACT-dpia-cross-border-transfer" in fact_ids


# ── Issue builder tests ──

def test_issue_builder_identifies_expected_issues() -> None:
    from backend.domains.eu.dpia.fact_builder import build_dpia_facts
    from backend.domains.eu.dpia.issue_builder import build_dpia_issues
    from backend.domains.eu.dpia.need_detector import DPIANeedDetector
    from backend.domains.eu.dpia.profile_extractor import DPIAProfileExtractor

    req = _make_valid_request()
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)
    diagnosis = DPIANeedDetector.evaluate(req)
    facts = build_dpia_facts(request=req, profile=profile, diagnosis_result=diagnosis)
    issues = build_dpia_issues(facts=facts, diagnosis_result=diagnosis, regulations=[], attachment_notes=[])
    issue_ids = {i.issue_id for i in issues}
    assert "DPIA-ISSUE-automated-decision" in issue_ids
    assert "DPIA-ISSUE-special-category" in issue_ids
    assert "DPIA-ISSUE-cross-border-risk" in issue_ids


# ── Evidence builder tests ──

def test_evidence_builder_links_issues_to_facts() -> None:
    from backend.domains.eu.dpia.evidence_builder import build_dpia_evidence
    from backend.domains.eu.dpia.fact_builder import build_dpia_facts
    from backend.domains.eu.dpia.issue_builder import build_dpia_issues
    from backend.domains.eu.dpia.need_detector import DPIANeedDetector
    from backend.domains.eu.dpia.profile_extractor import DPIAProfileExtractor

    req = _make_valid_request()
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)
    diagnosis = DPIANeedDetector.evaluate(req)
    facts = build_dpia_facts(request=req, profile=profile, diagnosis_result=diagnosis)
    issues = build_dpia_issues(facts=facts, diagnosis_result=diagnosis, regulations=[], attachment_notes=[])
    _, evidence_chain = build_dpia_evidence(facts=facts, issues=issues, regulations=[])
    assert len(evidence_chain) > 0
    for ev in evidence_chain:
        assert ev.evidence_id.startswith("DPIA-EVIDENCE-")
        assert ev.claim
        assert 0 <= ev.confidence <= 1.0


# ── Writing strategy tests ──

def test_writing_strategy_forbids_correct_expressions() -> None:
    from backend.domains.eu.dpia.writing_strategy_builder import build_writing_strategy
    from backend.common.workflow import IssueItem

    issue = IssueItem(
        issue_id="DPIA-ISSUE-automated-decision",
        title="自动化决策", description="涉及自动化决策",
        category="automated_decision", severity="HIGH",
        fact_refs=["F-1"], rule_refs=["GDPR Art 22"],
        recommended_action="补充人工干预机制",
        affects_outputs=["risk_assessment"],
    )
    strategy = build_writing_strategy([issue])
    assert "风险已完全消除" in strategy["global_forbidden_expressions"]
    assert "可直接上线" in strategy["global_forbidden_expressions"]


# ── Legal grounding tests ──

def test_legal_grounding_returns_expected_structure() -> None:
    from backend.domains.eu.dpia.legal_grounding import build_dpia_legal_grounding
    from backend.common.workflow import IssueItem, FactItem
    from backend.domains.eu.dpia.schema import RegulationHit

    facts = [FactItem(
        fact_id="F-1", source_type="schema", source_ref="test",
        field_path="dpia.automated_decision_making",
        value=True, normalized_value=True, confidence=0.6,
        evidence_status="user_claim_only", can_support_external_positive_claim=False,
    )]
    issues = [IssueItem(
        issue_id="DPIA-ISSUE-automated-decision",
        title="自动化决策", description="涉及自动化决策",
        category="automated_decision", severity="HIGH",
        fact_refs=["F-1"], rule_refs=["GDPR Article 22"],
        recommended_action="补充人工干预",
        affects_outputs=["risk_assessment"],
    )]
    regulations = [RegulationHit(
        source_id="reg-001", title="GDPR", article="Article 22",
        snippet="Automated individual decision-making safeguards.",
    )]
    legal, _ = build_dpia_legal_grounding(issues=issues, facts=facts, regulations=regulations)
    assert legal["grounding_version"] == "dpia-v1"
    assert "DPIA-ISSUE-automated-decision" in legal["by_issue"]


# ── Consistency checker tests ──

def test_consistency_checker_detects_missing_citations() -> None:
    from backend.domains.eu.dpia.consistency_checker import DPIAConsistencyChecker
    from backend.domains.eu.dpia.schema import DPIAChapterContent, DPIAProjectProfile

    profile = DPIAProjectProfile(
        project_name="测试", project_goal="测试",
        processing_flow_description="测试",
        data_categories=[], special_category_data=False,
        special_category_types=[], data_subject_categories=[],
        data_subject_count="", retention_period="",
        cross_border_transfer=False, transfer_destination="",
        automated_decision_making=False, systematic_monitoring=False,
        large_scale_processing=False, data_matching=False,
        new_technology=False, vulnerable_data_subjects=False,
        lawful_basis=[], dpia_trigger_reasons=[],
    )
    chapters = [DPIAChapterContent(chapter_no=1, title="测试章节", content="内容", citations=[])]
    checker = DPIAConsistencyChecker()
    issues = checker.check(profile, chapters)
    assert any("no citations" in i.lower() for i in issues)


# ── Profile extractor tests ──

def test_profile_extractor_handles_uploaded_files() -> None:
    from backend.domains.eu.dpia.profile_extractor import DPIAProfileExtractor

    req = _make_valid_request()
    extractor = DPIAProfileExtractor()
    profile = extractor.extract(req)
    assert profile.project_name == req.project_name
    assert profile.special_category_data is True
    assert profile.automated_decision_making is True
    assert profile.cross_border_transfer is True


# ══════════════════════════════════════════════════════════════════
# Full agent pipeline tests (fallback mode, no LLM network calls)
# ══════════════════════════════════════════════════════════════════

def test_full_pipeline_all_agents_run() -> None:
    """Verify the full 9-agent pipeline executes and produces all outputs."""
    svc = _make_service(use_llm=False)
    req = _make_valid_request()
    result = svc.generate_report(req)

    assert result.state == "COMPLETED"
    assert len(result.chapters) == 7
    assert len(result.output_files) > 0
    pdf_path = Path(result.output_files["pdf"])
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(pdf_path).pages) >= 1
    with ZipFile(result.output_files["zip"]) as bundle:
        assert pdf_path.name in bundle.namelist()

    # All agent outputs must be present
    assert result.need_assessment is not None
    assert result.need_assessment.dpia_required is True
    assert result.processing_activity_pack is not None
    assert result.necessity_findings is not None
    assert result.dpo_decision_pack is not None
    assert result.internal_ai_review is not None
    assert result.consistency_report is not None
    assert result.generation_basis_snapshot is not None
    assert result.trace_manifest_path

    # Risk matrix and mitigation plan must be populated
    assert len(result.risk_matrix) > 0
    assert len(result.mitigation_plan) > 0


def test_pipeline_empty_request_produces_minimal_output() -> None:
    """Pipeline should handle minimal valid request gracefully."""
    svc = _make_service(use_llm=False)
    req = DPIARequest.model_validate({
        "project_name": "最小项目", "project_goal": "最小目的",
        "processing_flow_description": "基本处理",
    })
    result = svc.generate_report(req)
    assert result.state == "COMPLETED"
    assert result.need_assessment is not None
    assert len(result.chapters) == 7


def test_dpia_need_agent_produces_triggers() -> None:
    """DPIA Need Agent should identify all high-risk trigger types."""
    svc = _make_service(use_llm=False)
    req = DPIARequest.model_validate({
        "project_name": "高风险项目", "project_goal": "AI面试筛选",
        "processing_flow_description": "视频面试 → AI评分 → HR决策",
        "automated_decision_making": True,
        "large_scale_processing": True,
        "special_category_data": True,
        "data_matching": True,
        "new_technology": True,
    })
    result = svc.generate_report(req)
    assert result.need_assessment.dpia_required is True
    assert len(result.need_assessment.trigger_reasons) >= 3


def test_necessity_agent_finds_questionable_processing() -> None:
    """Necessity agent should flag facial analysis as questionable."""
    from backend.domains.eu.dpia.agents.necessity_proportionality_agent import NecessityProportionalityAgent

    agent = NecessityProportionalityAgent(llm_client=None)
    result = agent.run(
        project_goal="AI招聘筛选",
        processing_activity_pack={
            "processing_steps": [
                {"step": "视频面试分析", "actor": "AI系统",
                 "processing": "分析面部表情和微表情，评估候选人情绪状态",
                 "risk_notes": ["可能推断情绪状态"]},
                {"step": "简历筛选", "actor": "HR系统",
                 "processing": "根据工作经验和教育背景评分"},
            ],
        },
        data_categories=["视频录制", "面部特征数据", "简历"],
    )
    findings = result
    assert len(findings["questionable_processing"]) > 0
    # Facial expression analysis should be flagged
    assert any("表情" in q.get("processing", "") or "面部" in q.get("processing", "")
               for q in findings["questionable_processing"])


def test_risk_assessment_produces_risk_matrix() -> None:
    """Risk assessment agent should produce a proper risk matrix."""
    from backend.domains.eu.dpia.agents.risk_assessment_agent import RiskAssessmentAgent

    agent = RiskAssessmentAgent(llm_client=None)
    result = agent.run(
        dpia_need_pack={"dpia_required": True, "trigger_reasons": [{"type": "automated_decision_making"}]},
        processing_activity_pack={
            "processing_steps": [
                {"step": "自动化评分和排名", "actor": "AI", "processing": "自动评分"},
            ],
            "cross_border_transfer": {"exists": True, "destination": "US"},
        },
        necessity_findings={},
        user_identified_risks=["歧视性决策"],
    )
    assert len(result["risk_matrix"]) >= 3
    assert any(r["overall_level"] == "HIGH" for r in result["risk_matrix"])


def test_dpo_agent_recommends_prior_consultation() -> None:
    """DPO agent should recommend prior consultation when HIGH residual risks remain."""
    from backend.domains.eu.dpia.agents.dpo_consultation_agent import DPOConsultationAgent

    agent = DPOConsultationAgent(llm_client=None)
    result = agent.run(
        risk_matrix=[
            {"risk_id": "RISK-1", "risk_name": "高风险", "overall_level": "HIGH",
             "likelihood": "MEDIUM", "impact": "HIGH"},
        ],
        mitigation_plan=[
            {"risk_id": "RISK-1", "measures": [], "residual_risk": "HIGH"},
        ],
        dpo_opinion="需要更多时间评估",
        remaining_high_risks=["RISK-1"],
    )
    assert result["prior_consultation_recommended"] is True
    assert result["dpo_position"] in ("conditional_approval", "objection")
    assert result["source_opinion"] == "需要更多时间评估"
    assert result["decision_basis"] == "structured_risk_assessment"


def test_dpo_agent_does_not_promote_user_comment_to_formal_dpo_approval() -> None:
    """Critical sign-off fields must come from rules, not generated attribution."""
    from backend.domains.eu.dpia.agents.dpo_consultation_agent import DPOConsultationAgent

    class _OverclaimingLLM:
        enabled = True

        def chat(self, **_kwargs):
            return '''{
              "dpo_position": "approval",
              "conditions": [],
              "prior_consultation_recommended": false,
              "reason": "DPO formally approved launch",
              "draft_text": "DPO已正式无条件批准上线"
            }'''

    result = DPOConsultationAgent(_OverclaimingLLM()).run(
        risk_matrix=[{"risk_id": "RISK-1", "overall_level": "HIGH"}],
        mitigation_plan=[{"risk_id": "RISK-1", "measures": [], "residual_risk": "HIGH"}],
        dpo_opinion="建议上线但需要持续监控推荐质量指标",
        remaining_high_risks=["RISK-1"],
    )

    assert result["prior_consultation_recommended"] is True
    assert result["dpo_position"] != "approval"
    assert result["source_opinion"] == "建议上线但需要持续监控推荐质量指标"
    assert "正式" not in result["draft_text"]


def test_internal_review_recommends_delay() -> None:
    """Internal review should recommend delay when HIGH risks present."""
    from backend.domains.eu.dpia.agents.internal_review_agent import InternalReviewAgent

    agent = InternalReviewAgent(llm_client=None)
    result = agent.run(
        risk_matrix=[
            {"risk_id": "RISK-1", "risk_name": "严重风险", "overall_level": "HIGH",
             "likelihood": "HIGH", "impact": "HIGH"},
        ],
        mitigation_plan=[
            {"risk_id": "RISK-1", "measures": [
                {"measure": "计划进行审计", "status": "planned"}
            ], "residual_risk": "HIGH"},
        ],
        dpo_decision_pack={"dpo_position": "conditional_approval", "conditions": ["完成审计"]},
        user_claim_only_facts=["用户声称已取得全部数据主体同意"],
    )
    assert result["recommend_delay_launch"] is True
    assert len(result["high_risk_issues"]) > 0
    assert len(result["draft_text"]) > 0


def test_long_structured_agents_have_non_truncating_token_budgets() -> None:
    from backend.domains.eu.dpia.agents.internal_review_agent import InternalReviewAgent
    from backend.domains.eu.dpia.agents.mitigation_mapping_agent import MitigationMappingAgent

    assert MitigationMappingAgent.max_tokens >= 2000
    assert InternalReviewAgent.max_tokens >= 2000


def test_consistency_agent_finds_missing_mitigation() -> None:
    """Consistency agent should flag HIGH risks without mitigation."""
    from backend.domains.eu.dpia.agents.consistency_repair_agent import ConsistencyRepairAgent

    agent = ConsistencyRepairAgent(llm_client=None)
    result = agent.run(
        draft_chapters=[],
        risk_matrix=[
            {"risk_id": "RISK-1", "risk_name": "高风险", "overall_level": "HIGH",
             "likelihood": "HIGH", "impact": "HIGH"},
        ],
        mitigation_plan=[],  # Empty — no mitigation at all
    )
    assert result["checks_passed"] < result["checks_total"]
    blocking = result.get("blocking_issues", [])
    assert any("RISK-1" in str(b) or "mitigation" in str(b).lower() for b in blocking)


def test_consistency_agent_removes_resolved_citation_and_conservative_claim_false_positives() -> None:
    from backend.domains.eu.dpia.agents.consistency_repair_agent import ConsistencyRepairAgent

    class _FalsePositiveLLM:
        enabled = True

        def chat(self, **_kwargs):
            return """{
              "checks_passed": 8,
              "checks_total": 10,
              "blocking_issues": [
                {"check":"check_fabricated_citations","finding":"[1] is not defined","severity":"HIGH"},
                {"check":"check_user_claim_as_fact","finding":"用户表示已通过隐私政策告知","severity":"MEDIUM"},
                {"check":"check_dpo_conditions_in_conclusion","finding":"DPO opinion is inconsistent","severity":"HIGH"}
              ],
              "repairs_applied": [],
              "needs_manual_review": true,
              "final_status": "blocked",
              "draft_text": "review"
            }"""

    result = ConsistencyRepairAgent(_FalsePositiveLLM()).run(
        draft_chapters=[{"content": (
            "根据 GDPR 第35条需要评估[1]。用户表示已通过隐私政策告知。"
            "用户填写的 DPO 意见为：建议上线。该输入不等同于正式 DPO 签署或批准。"
            "结构化风险评估结论：conditional_approval。"
        )}],
        known_citations=["CIT-EU-EU_LAW_001-ART35-P01"],
    )

    assert result["blocking_issues"] == []
    assert result["needs_manual_review"] is False
    assert result["final_status"] == "ready"


def test_consistency_agent_records_unapplied_edits_as_suggestions() -> None:
    from backend.domains.eu.dpia.agents.consistency_repair_agent import ConsistencyRepairAgent

    class _LegacyRepairLLM:
        enabled = True

        def chat(self, **_kwargs):
            return '''{
              "checks_passed": 9,
              "checks_total": 10,
              "blocking_issues": [],
              "repairs_applied": [
                {"check":"style","original":"原文","repaired":"建议文本"}
              ],
              "needs_manual_review": false,
              "final_status": "ready",
              "draft_text": "review"
            }'''

    result = ConsistencyRepairAgent(_LegacyRepairLLM()).run(
        draft_chapters=[{"content": "原文"}],
    )

    assert result["repairs_applied"] == []
    assert result["repair_suggestions"][0]["repaired"] == "建议文本"


def test_external_draft_enforces_article_36_conclusion_when_dpo_requires_it() -> None:
    from backend.common.citation.registry import registry_from_documents
    from backend.domains.eu.dpia.agents.external_draft_agent import ExternalDPIAgent

    class _GenericDraftLLM:
        enabled = True

        def chat(self, **_kwargs):
            return '{"content":"本章内容。","citations":[],"risk_level":"medium"}'

    registry = registry_from_documents(
        [{
            "source_id": "EU-LAW-001",
            "title": "GDPR (EU) 2016/679",
            "article": "36",
            "snippet": "Prior consultation.",
        }],
        jurisdiction="EU",
    )
    chapters = ExternalDPIAgent(_GenericDraftLLM()).run(
        generation_basis_pack={
            "section_packs": [
                {"section_id": key, "confirmed_facts": [], "issues": [], "legal_grounding": []}
                for key in (
                    "need_identification", "processing_description", "consultation",
                    "necessity_proportionality", "risk_assessment", "mitigation", "signoff",
                )
            ],
            "dpo_decision_pack": {
                "prior_consultation_recommended": True,
                "reason": "缓解后仍有高剩余风险",
            },
            "citations": registry.to_list(),
        },
        citation_registry=registry,
    )

    signoff = chapters[-1]
    assert "必须在开始处理前" in signoff["content"]
    assert "[1]" in signoff["content"]
    assert next(iter(registry)).citation_id in signoff["citations"]


def test_external_draft_uses_structured_chapters_for_consultation_and_signoff() -> None:
    """User-entered DPO text must not be rewritten as a signed formal approval."""
    from backend.domains.eu.dpia.agents.external_draft_agent import ExternalDPIAgent

    class _OverclaimingDraftLLM:
        enabled = True

        def chat(self, **_kwargs):
            return '{"content":"DPO已正式审阅并无条件批准上线。","citations":[],"risk_level":"low"}'

    section_packs = [
        {"section_id": key, "confirmed_facts": [], "issues": [], "legal_grounding": []}
        for key in (
            "need_identification", "processing_description", "consultation",
            "necessity_proportionality", "risk_assessment", "mitigation", "signoff",
        )
    ]
    for section in section_packs:
        if section["section_id"] in {"consultation", "signoff"}:
            section["confirmed_facts"] = [
                {
                    "field_path": "dpia.dpo_opinion",
                    "value": "建议上线但需要持续监控推荐质量指标",
                    "evidence_status": "user_claim_only",
                }
            ]

    chapters = ExternalDPIAgent(_OverclaimingDraftLLM()).run(
        generation_basis_pack={
            "section_packs": section_packs,
            "dpo_decision_pack": {
                "dpo_position": "conditional_approval",
                "conditions": ["验证计划措施"],
                "prior_consultation_recommended": True,
                "reason": "存在HIGH剩余风险",
                "source_opinion": "建议上线但需要持续监控推荐质量指标",
                "decision_basis": "structured_risk_assessment",
            },
        },
    )

    consultation = chapters[2]["content"]
    signoff = chapters[-1]["content"]
    assert "用户填写的 DPO 意见" in consultation
    assert "不等同于正式签署或批准" in consultation
    assert "结构化风险评估结论" in signoff
    assert "DPO已正式审阅" not in consultation + signoff


def test_external_draft_rejects_provable_cross_chapter_contradictions() -> None:
    from backend.domains.eu.dpia.agents.external_draft_agent import ExternalDPIAgent

    class _ContradictingLLM:
        enabled = True

        def chat(self, **_kwargs):
            return '{"content":"目前无任何缓解措施，DPO意见未提供。","citations":[],"risk_level":"high"}'

    section_ids = (
        "need_identification", "processing_description", "consultation",
        "necessity_proportionality", "risk_assessment", "mitigation", "signoff",
    )
    chapters = ExternalDPIAgent(_ContradictingLLM()).run(
        generation_basis_pack={
            "section_packs": [
                {"section_id": key, "confirmed_facts": [], "issues": [], "legal_grounding": []}
                for key in section_ids
            ],
            "risk_matrix": [{"risk_id": "RISK-1", "overall_level": "HIGH"}],
            "mitigation_plan": [{
                "risk_id": "RISK-1",
                "measures": [{"measure": "人工复核", "status": "planned"}],
                "residual_risk": "HIGH",
            }],
            "dpo_decision_pack": {
                "source_opinion": "建议上线但持续监控",
                "prior_consultation_recommended": True,
                "decision_basis": "structured_risk_assessment",
            },
        },
    )

    combined = "\n".join(chapter["content"] for chapter in chapters)
    assert "目前无任何缓解措施" not in combined
    assert "DPO意见未提供" not in combined
    assert "人工复核" in chapters[5]["content"]


def test_external_draft_no_llm_path_keeps_citations_and_article36_decision() -> None:
    from backend.common.citation.registry import registry_from_documents
    from backend.domains.eu.dpia.agents.external_draft_agent import ExternalDPIAgent

    registry = registry_from_documents(
        [
            {
                "source_id": "EU-LAW-001",
                "title": "GDPR (EU) 2016/679",
                "article": article,
                "snippet": f"Article {article}",
                "confidence_score": 0.9,
            }
            for article in ("22", "35", "36")
        ],
        jurisdiction="EU",
    )
    section_ids = (
        "need_identification", "processing_description", "consultation",
        "necessity_proportionality", "risk_assessment", "mitigation", "signoff",
    )
    chapters = ExternalDPIAgent(llm_client=None).run(
        generation_basis_pack={
            "section_packs": [
                {"section_id": key, "confirmed_facts": [], "issues": [], "legal_grounding": []}
                for key in section_ids
            ],
            "need_assessment": {"dpia_required": True},
            "dpo_decision_pack": {
                "prior_consultation_recommended": True,
                "reason": "存在HIGH剩余风险",
            },
        },
        citation_registry=registry,
    )

    assert "[" in chapters[0]["content"]
    assert "必须在开始处理前" in chapters[-1]["content"]
    assert any(chapter["citations"] for chapter in chapters)


def test_processing_activity_extracts_data_flow() -> None:
    """Processing activity agent should parse data flow into structured steps."""
    from backend.domains.eu.dpia.agents.processing_activity_agent import ProcessingActivityAgent

    agent = ProcessingActivityAgent(llm_client=None)
    # Test with incomplete data — missing retention should trigger ambiguity
    result = agent.run(
        raw_inputs={
            "data_flow": "求职者→招聘网站→AWS欧盟→AI模型→HR系统",
            "data_types": ["简历", "视频/音频", "在线测试答案"],
            "cross_border": "美国团队",
        },
    )
    assert len(result["processing_steps"]) > 0
    assert result["cross_border_transfer"]["exists"] is True
    assert len(result["ambiguities"]) > 0

    # Test with clear data flow (no arrows) — should flag ambiguity
    result2 = agent.run(
        raw_inputs={
            "data_flow": "Vague description without structure",
            "data_types": ["通用数据"],
        },
    )
    assert len(result2["ambiguities"]) > 0


def test_external_draft_produces_all_7_chapters() -> None:
    """External draft agent should produce placeholder chapters when LLM unavailable."""
    from backend.domains.eu.dpia.agents.external_draft_agent import ExternalDPIAgent

    agent = ExternalDPIAgent(llm_client=None)
    chapters = agent.run(generation_basis_pack={})
    assert len(chapters) == 7
    for ch in chapters:
        assert ch.get("chapter_no", 0) > 0
        assert ch.get("title")
        assert ch.get("content")


def test_external_draft_prompt_uses_generation_basis_contract() -> None:
    """The chapter prompt must include facts and legal sources from the basis pack."""
    from backend.domains.eu.dpia.agents.external_draft_agent import _build_chapter_prompt

    prompt = _build_chapter_prompt(
        chapter_id="processing_description",
        title="2. 描述处理活动",
        section={},
        gen_basis={
            "user_facts": [
                {"field_path": "dpia.project_name", "value": "智能课程推荐系统"},
                {"field_path": "dpia.data_subject_count", "value": "50000"},
            ],
            "regulations": [
                {
                    "source_id": "CIT-EU-GDPR-ART35-P01",
                    "title": "GDPR",
                    "article": "35",
                }
            ],
            "issues": [],
            "risk_matrix": [],
            "mitigation_plan": [],
            "dpo_decision_pack": {},
            "need_assessment": {"dpia_required": True},
            "legal_grounding": {},
        },
        writing={},
    )

    assert "智能课程推荐系统" in prompt
    assert "50000" in prompt
    assert "CIT-EU-GDPR-ART35-P01" in prompt
    assert "项目事实：\n未提供" not in prompt
    assert "法规依据：\n无引用" not in prompt


def test_generation_basis_routes_consultation_and_lawful_basis_facts_to_sections() -> None:
    from backend.domains.eu.dpia.evidence_builder import build_dpia_evidence
    from backend.domains.eu.dpia.fact_builder import build_dpia_facts
    from backend.domains.eu.dpia.generation_basis import build_generation_basis_pack
    from backend.domains.eu.dpia.issue_builder import build_dpia_issues
    from backend.domains.eu.dpia.need_detector import DPIANeedDetector
    from backend.domains.eu.dpia.profile_extractor import DPIAProfileExtractor

    request = _make_valid_request()
    profile = DPIAProfileExtractor().extract(request)
    diagnosis = DPIANeedDetector.evaluate(request)
    facts = build_dpia_facts(request, profile, diagnosis)
    issues = build_dpia_issues(facts, diagnosis, [], [])
    issues, evidence = build_dpia_evidence(facts, issues, [], diagnosis)
    pack = build_generation_basis_pack(
        task_id="section-facts",
        facts=facts,
        issues=issues,
        evidence_chain=evidence,
        regulations=[],
        attachment_notes=[],
    )
    sections = {item["section_id"]: item for item in pack["section_packs"]}
    consultation_paths = {
        item["field_path"] for item in sections["consultation"]["confirmed_facts"]
    }
    necessity_paths = {
        item["field_path"]
        for item in sections["necessity_proportionality"]["confirmed_facts"]
    }

    assert "dpia.consulted_internal_departments" in consultation_paths
    assert "dpia.data_subject_consultation_plan" in consultation_paths
    assert "dpia.dpo_opinion" in consultation_paths
    assert "dpia.lawful_basis" in necessity_paths


def test_external_draft_prompt_prefers_section_facts_over_global_prefix() -> None:
    from backend.domains.eu.dpia.agents.external_draft_agent import _build_chapter_prompt

    prompt = _build_chapter_prompt(
        chapter_id="necessity_proportionality",
        title="4. 必要性与相称性评估",
        section={
            "confirmed_facts": [
                {
                    "field_path": "dpia.lawful_basis",
                    "value": ["GDPR Art 6(1)(a) 同意", "GDPR Art 6(1)(f) 正当利益"],
                }
            ],
            "issues": [],
        },
        gen_basis={
            "user_facts": [
                {"field_path": f"dpia.unrelated_{index}", "value": index}
                for index in range(20)
            ],
            "citations": [],
            "risk_matrix": [],
            "mitigation_plan": [],
            "dpo_decision_pack": {},
            "need_assessment": {},
            "legal_grounding": {},
        },
        writing={},
    )

    assert "GDPR Art 6(1)(a) 同意" in prompt
    assert "unrelated_0" not in prompt


def test_external_draft_uses_structured_fallback_instead_of_placeholder() -> None:
    from backend.common.citation.registry import registry_from_documents
    from backend.domains.eu.dpia.agents.external_draft_agent import ExternalDPIAgent

    class _TimeoutLLM:
        enabled = True

        def chat(self, **_kwargs):
            return "Request timed out."

    registry = registry_from_documents(
        [
            {
                "source_id": "EU-LAW-001",
                "title": "GDPR (EU) 2016/679",
                "article": article,
                "snippet": f"Article {article}",
            }
            for article in ("5", "6", "13", "14", "22", "35", "36")
        ],
        jurisdiction="EU",
    )
    section_packs = [
        {"section_id": section_id, "confirmed_facts": [], "issues": [], "legal_grounding": []}
        for section_id in (
            "need_identification",
            "processing_description",
            "consultation",
            "necessity_proportionality",
            "risk_assessment",
            "mitigation",
            "signoff",
        )
    ]
    section_packs[2]["confirmed_facts"] = [
        {"field_path": "dpia.consulted_internal_departments", "value": ["法务部", "IT部门"]},
        {"field_path": "dpia.data_subject_consultation_plan", "value": "学生代表会议"},
    ]
    section_packs[3]["confirmed_facts"] = [
        {"field_path": "dpia.lawful_basis", "value": ["GDPR Art 6(1)(a) 同意"]},
        {"field_path": "dpia.necessity_statement", "value": "个性化推荐所必需"},
    ]
    chapters = ExternalDPIAgent(_TimeoutLLM()).run(
        generation_basis_pack={
            "section_packs": section_packs,
            "need_assessment": {
                "dpia_required": True,
                "trigger_reasons": ["automated_decision_making"],
                "prior_consultation_possible": True,
            },
            "processing_activity_pack": {"draft_text": "收集并分析学生学习行为数据。"},
            "necessity_findings": {"draft_text": "数据范围和保留期仍需进一步证明。"},
            "risk_matrix": [],
            "mitigation_plan": [],
            "dpo_decision_pack": {
                "dpo_position": "conditional_approval",
                "conditions": ["上线前完成人工复核机制"],
                "prior_consultation_recommended": True,
            },
            "citations": registry.to_list(),
        },
        citation_registry=registry,
    )

    assert len(chapters) == 7
    assert all("Agent不可用" not in chapter["content"] for chapter in chapters)
    assert all("LLM未配置" not in chapter["content"] for chapter in chapters)
    assert "法务部" in chapters[2]["content"]
    assert "学生代表会议" in chapters[2]["content"]
    assert "GDPR Art 6(1)(a) 同意" in chapters[3]["content"]
    assert any("[" in chapter["content"] for chapter in chapters)


def test_agent_json_parse_fallback_is_written_to_trace(tmp_path) -> None:
    """Malformed model JSON must be visible in trace and fallback metrics."""
    import json

    from backend.common.runtime.run_manifest import summarize_trace
    from backend.common.trace.context import current_trace
    from backend.common.trace.recorder import TraceRecorder
    from backend.domains.eu.dpia.agents import DPIAAgentBase

    class _MalformedJSONLLM:
        enabled = True

        def chat(self, **_kwargs):
            return '{"content": "broken"'

    class _TestAgent(DPIAAgentBase):
        agent_name = "trace_test_agent"

    recorder = TraceRecorder(tmp_path / "trace", task_id="agent-fallback")
    token = current_trace.set(recorder)
    try:
        result = _TestAgent(_MalformedJSONLLM())._call_llm("test")
    finally:
        current_trace.reset(token)

    assert result is None
    fallback = json.loads(
        (tmp_path / "trace" / "001_agent_fallback.json").read_text(
            encoding="utf-8"
        )
    )
    assert fallback["payload"]["detail"]["agent"] == "trace_test_agent"
    assert fallback["payload"]["detail"]["fallback"] is True
    assert summarize_trace(recorder)["fallback_count"] == 1


def test_external_draft_converts_registered_citation_markers() -> None:
    from backend.common.citation.registry import registry_from_documents
    from backend.domains.eu.dpia.agents.external_draft_agent import ExternalDPIAgent

    registry = registry_from_documents(
        [{
            "source_id": "EU-LAW-001",
            "title": "GDPR (EU) 2016/679",
            "article": "35",
            "snippet": "Article 35 requires a DPIA for likely high-risk processing.",
        }],
        jurisdiction="EU",
    )
    citation_id = next(iter(registry)).citation_id

    class _MarkerLLM:
        enabled = True

        def chat(self, **_kwargs):
            return (
                '{"content":"该处理需要开展DPIA {{'
                + citation_id
                + '}}。","citations":["'
                + citation_id
                + '"],"risk_level":"high"}'
            )

    chapters = ExternalDPIAgent(_MarkerLLM()).run(
        generation_basis_pack={
            "user_facts": [{"value": "高风险处理"}],
            "citations": registry.to_list(),
        },
        citation_registry=registry,
    )

    assert len(chapters) == 7
    assert all("{{CIT-" not in chapter["content"] for chapter in chapters)
    # Consultation and sign-off are now compiled from structured records; the
    # remaining model-drafted chapters still normalize registered markers.
    for chapter_index in (0, 1, 3, 4, 5):
        assert "[1]" in chapters[chapter_index]["content"]
    assert registry.get_footnote_map()[1].citation_id == citation_id


def test_grounded_citation_registry_uses_best_article_binding() -> None:
    from backend.domains.eu.dpia.schema import RegulationHit
    from backend.domains.eu.dpia.service import _build_grounded_citation_registry

    registry = _build_grounded_citation_registry(
        [
            RegulationHit(
                source_id="EU-LAW-001",
                title="GDPR (EU) 2016/679",
                article="22",
                snippet="Automated decision-making safeguards.",
                authority_level="high",
                binding_force="mandatory",
            )
        ],
        {
            "by_issue": {
                "DPIA-ISSUE-automated-decision": [
                    {
                        "rule_id": "EU-LAW-001",
                        "article": "22",
                        "confidence_score": 0.88,
                        "authority_level": "high",
                        "binding_force": "mandatory",
                        "source_kind": "law_article",
                        "allowed_usage": ["external_report", "internal_review"],
                        "can_enter_external_report": True,
                        "confidence_threshold": 0.30,
                        "external_report_allowed": True,
                    }
                ]
            }
        },
    )

    item = next(iter(registry))
    assert item.confidence_score == 0.88
    assert item.authority_level == "high"
    assert item.binding_force == "mandatory"
    assert item.external_report_allowed is True


def test_grounded_citation_registry_scores_direct_structured_article_signals() -> None:
    from backend.domains.eu.dpia.schema import RegulationHit
    from backend.domains.eu.dpia.service import _build_grounded_citation_registry

    registry = _build_grounded_citation_registry(
        [
            RegulationHit(
                source_id="EU-LAW-001",
                title="GDPR (EU) 2016/679",
                article="6",
                snippet="Lawfulness of processing.",
                authority_level="high",
                binding_force="mandatory",
            ),
            RegulationHit(
                source_id="EU-LAW-001",
                title="GDPR (EU) 2016/679",
                article="9",
                snippet="Special categories of personal data.",
                authority_level="high",
                binding_force="mandatory",
            ),
        ],
        {"by_issue": {}},
        fact_values=["GDPR Art 6(1)(a) 同意"],
        risk_matrix=[{"risk_name": "特殊类别数据推断风险"}],
    )

    by_article = {item.article_no: item for item in registry}
    assert by_article["6"].confidence_score >= 0.9
    assert by_article["9"].confidence_score >= 0.9
    assert by_article["6"].external_report_allowed is True
    assert by_article["9"].external_report_allowed is True
