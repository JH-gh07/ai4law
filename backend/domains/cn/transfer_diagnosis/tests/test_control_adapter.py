"""task073 T03-T05 — Diagnosis 控制门纯函数单元测试（G1/G2/G4）。"""
from __future__ import annotations

from backend.common.legal_control.contracts import LegalControlDecision, merge_gate_results
from backend.domains.cn.transfer_diagnosis.control_adapter import (
    build_fact_completeness_gate,
    build_rule_precedence_gate,
)
from backend.domains.cn.transfer_diagnosis.models import (
    DiagnosisFacts,
    FactSource,
    TriState,
)
from backend.domains.cn.transfer_diagnosis.rule_engine import RuleMatch
from backend.domains.cn.transfer_diagnosis.schema import DiagnosisResult


def _facts(**overrides) -> DiagnosisFacts:
    base = {
        "is_ciio": TriState.NO,
        "contains_important_data": TriState.NO,
        "personal_info_count": 100,
        "sensitive_personal_info_count": 10,
        "no_personal_info": TriState.NO,
    }
    base.update(overrides)
    return DiagnosisFacts(**base)


def _conflict_result() -> DiagnosisResult:
    return DiagnosisResult(
        recommended_path="manual_review",
        legal_basis=[],
        rationale="事实冲突",
        action_items=[],
        risk_level="HIGH",
        conclusion_source="validation",
        uncertainty_notes=["q5 声明与个人信息字段冲突。"],
    )


# ── G1 ──────────────────────────────────────────────────────────────────

def test_g1_pass_when_no_missing_and_no_conflict():
    gate = build_fact_completeness_gate(
        facts=_facts(),
        validation_result=None,
        clarification_questions=[],
    )
    assert gate.gate == "FACT_COMPLETENESS"
    assert gate.outcome == "PASS"


def test_g1_critical_missing_escalates_and_adds_question():
    questions: list[str] = []
    facts = _facts(
        is_ciio=TriState.UNKNOWN,
        missing_facts=["is_ciio"],
    )
    gate = build_fact_completeness_gate(
        facts=facts,
        validation_result=None,
        clarification_questions=questions,
    )
    assert gate.outcome == "ESCALATE"
    assert gate.details["critical_missing"] == ["is_ciio"]
    assert gate.refs == ["is_ciio"]
    assert len(questions) == 1
    assert "CIIO" in questions[0]


def test_g1_conflict_escalates_without_critical_missing():
    gate = build_fact_completeness_gate(
        facts=_facts(),
        validation_result=_conflict_result(),
        clarification_questions=[],
    )
    assert gate.outcome == "ESCALATE"
    assert "critical_missing" not in gate.details
    assert gate.details["conflicts"]


def test_g1_conflict_maps_to_needs_review():
    gate = build_fact_completeness_gate(
        facts=_facts(),
        validation_result=_conflict_result(),
        clarification_questions=[],
    )
    decision = merge_gate_results([gate])
    assert decision.legal_control_status == "NEEDS_REVIEW"


def test_g1_critical_missing_maps_to_needs_clarification():
    gate = build_fact_completeness_gate(
        facts=_facts(is_ciio=TriState.UNKNOWN, missing_facts=["is_ciio"]),
        validation_result=None,
        clarification_questions=[],
    )
    decision = merge_gate_results([gate])
    assert decision.legal_control_status == "NEEDS_CLARIFICATION"


# ── G2 ──────────────────────────────────────────────────────────────────

def test_g2_non_default_rule_locks_path():
    facts = _facts()
    facts.field_provenance["personal_info_count"] = FactSource.USER
    rule = RuleMatch(
        rule_id="pii_threshold",
        path="security_assessment",
        condition_fields=["q3_pii_count_gte"],
        is_default=False,
    )
    gate = build_rule_precedence_gate(rule_match=rule, facts=facts)
    assert gate.outcome == "PASS"
    assert gate.details["execution_precedence"] is True


def test_g2_decisive_llm_inference_escalates():
    facts = _facts(contains_important_data=TriState.YES)
    facts.field_provenance["contains_important_data"] = FactSource.LLM_INFERENCE
    rule = RuleMatch(
        rule_id="important_data",
        path="security_assessment",
        condition_fields=["q2_has_important_data"],
        is_default=False,
    )
    gate = build_rule_precedence_gate(rule_match=rule, facts=facts)
    assert gate.outcome == "ESCALATE"
    assert gate.details["decisive_inferred"] == ["contains_important_data"]
    decision = merge_gate_results([gate])
    assert decision.legal_control_status == "NEEDS_REVIEW"


def test_g2_decisive_default_provenance_escalates():
    """DEFAULT 来源的决定性事实同样升级为 NEEDS_REVIEW。"""
    facts = _facts(contains_important_data=TriState.YES)
    facts.field_provenance["contains_important_data"] = FactSource.DEFAULT
    rule = RuleMatch(
        rule_id="important_data",
        path="security_assessment",
        condition_fields=["q2_has_important_data"],
        is_default=False,
    )
    gate = build_rule_precedence_gate(rule_match=rule, facts=facts)
    assert gate.outcome == "ESCALATE"
    assert gate.details["decisive_inferred"] == ["contains_important_data"]


def test_g2_default_branch_keeps_ai_inference_unlocked():
    rule = RuleMatch(
        rule_id="default",
        path="scc_or_certification",
        is_default=True,
    )
    gate = build_rule_precedence_gate(rule_match=rule, facts=_facts())
    assert gate.outcome == "CONDITIONAL"
    assert gate.details["execution_precedence"] is False


# ── G4 ──────────────────────────────────────────────────────────────────

def test_g4_priority_merge():
    g1 = build_fact_completeness_gate(
        facts=_facts(is_ciio=TriState.UNKNOWN, missing_facts=["is_ciio"]),
        validation_result=None,
        clarification_questions=[],
    )
    g2 = build_rule_precedence_gate(
        rule_match=RuleMatch(rule_id="default", path="scc_or_certification", is_default=True),
        facts=_facts(is_ciio=TriState.UNKNOWN),
    )
    decision = merge_gate_results([g1, g2])
    # NEEDS_CLARIFICATION (2) 优先于 CONDITIONAL (1)
    assert decision.legal_control_status == "NEEDS_CLARIFICATION"
    assert decision.gate_results[0].gate == "FACT_COMPLETENESS"
    assert decision.gate_results[1].gate == "RULE_PRECEDENCE"
