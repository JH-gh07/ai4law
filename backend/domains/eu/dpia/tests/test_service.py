"""Test DPIA service — lower-level components + full 9-agent pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pytest
from pypdf import PdfReader

from backend.domains.eu.dpia.schema import DPIARequest, DPIAResult
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
