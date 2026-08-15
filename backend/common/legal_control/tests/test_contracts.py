"""task073 T01 — Legal Control 契约与聚合单测。"""
from __future__ import annotations

import pytest

from backend.common.legal_control.contracts import (
    LegalControlDecision,
    LegalControlGateResult,
    merge_gate_results,
)
from backend.common.reporting.render_manifest import GateResult as RenderGateResult


def _gate(gate, outcome, **kwargs) -> LegalControlGateResult:
    return LegalControlGateResult(gate=gate, outcome=outcome, **kwargs)


class TestEmptyDecision:
    def test_no_gates_defaults_to_auto(self):
        decision = merge_gate_results([])
        assert decision.legal_control_status == "AUTO"
        assert decision.gate_results == []
        assert decision.reasons == []
        assert decision.required_actions == []


class TestSingleGate:
    def test_pass_keeps_auto(self):
        decision = merge_gate_results([_gate("RULE_PRECEDENCE", "PASS")])
        assert decision.legal_control_status == "AUTO"

    def test_conditional_maps_to_conditional(self):
        decision = merge_gate_results([_gate("EVIDENCE_SUFFICIENCY", "CONDITIONAL")])
        assert decision.legal_control_status == "CONDITIONAL"

    def test_escalate_maps_to_needs_review(self):
        decision = merge_gate_results([_gate("CITATION_VALIDITY", "ESCALATE")])
        assert decision.legal_control_status == "NEEDS_REVIEW"

    def test_block_maps_to_blocked(self):
        decision = merge_gate_results([_gate("ESCALATION", "BLOCK")])
        assert decision.legal_control_status == "BLOCKED"


class TestFactCompletenessCriticalMissing:
    def test_g1_critical_missing_maps_to_needs_clarification(self):
        gr = _gate(
            "FACT_COMPLETENESS",
            "ESCALATE",
            details={"critical_missing": ["is_ciio"]},
            reasons=["关键事实缺失"],
            required_actions=["补充缺失事实"],
        )
        decision = merge_gate_results([gr])
        assert decision.legal_control_status == "NEEDS_CLARIFICATION"

    def test_g1_escalate_without_critical_missing_maps_to_needs_review(self):
        # 冲突/决定性推断：ESCALATE 但不带 critical_missing → NEEDS_REVIEW
        gr = _gate(
            "FACT_COMPLETENESS",
            "ESCALATE",
            details={"conflicts": ["q5 与 q2 冲突"]},
        )
        decision = merge_gate_results([gr])
        assert decision.legal_control_status == "NEEDS_REVIEW"


class TestMergePriority:
    def test_blocked_dominates_all(self):
        decision = merge_gate_results(
            [
                _gate("FACT_COMPLETENESS", "ESCALATE", details={"critical_missing": ["is_ciio"]}),
                _gate("ESCALATION", "BLOCK"),
                _gate("CITATION_VALIDITY", "CONDITIONAL"),
            ]
        )
        assert decision.legal_control_status == "BLOCKED"

    def test_needs_review_dominates_needs_clarification(self):
        decision = merge_gate_results(
            [
                _gate("FACT_COMPLETENESS", "ESCALATE", details={"critical_missing": ["is_ciio"]}),
                _gate("CITATION_VALIDITY", "ESCALATE"),
            ]
        )
        assert decision.legal_control_status == "NEEDS_REVIEW"

    def test_priority_is_independent_of_input_order(self):
        gates = [
            _gate("CITATION_VALIDITY", "ESCALATE"),
            _gate("FACT_COMPLETENESS", "ESCALATE", details={"critical_missing": ["is_ciio"]}),
        ]
        assert merge_gate_results(gates).legal_control_status == "NEEDS_REVIEW"
        assert merge_gate_results(list(reversed(gates))).legal_control_status == "NEEDS_REVIEW"


class TestAggregation:
    def test_reasons_and_actions_are_deduped_in_order(self):
        decision = merge_gate_results(
            [
                _gate("CITATION_VALIDITY", "ESCALATE", reasons=["r1", "r2"], required_actions=["a1"]),
                _gate("EVIDENCE_SUFFICIENCY", "CONDITIONAL", reasons=["r2", "r3"], required_actions=["a1", "a2"]),
            ]
        )
        assert decision.reasons == ["r1", "r2", "r3"]
        assert decision.required_actions == ["a1", "a2"]

    def test_gate_results_preserved(self):
        gates = [_gate("CITATION_VALIDITY", "ESCALATE")]
        decision = merge_gate_results(gates)
        assert decision.gate_results == gates


class TestNamespaceIsolation:
    def test_legal_control_gate_result_does_not_reuse_render_gate_result(self):
        """同名 GateResult 契约隔离：字段集合不同，序列化互不污染。"""
        legal_fields = set(LegalControlGateResult.model_fields)
        render_fields = set(RenderGateResult.model_fields)
        # render_manifest.GateResult 的字段 name/status/diagnostics 不应出现在 Legal Control
        assert {"name", "status", "diagnostics"}.isdisjoint(legal_fields)
        # Legal Control 的 gate/outcome/reasons/refs/required_actions/details 不应出现在 render
        assert {"gate", "outcome", "reasons", "refs", "required_actions", "details"}.isdisjoint(render_fields)

    def test_decision_json_roundtrip(self):
        decision = merge_gate_results(
            [_gate("FACT_COMPLETENESS", "ESCALATE", details={"critical_missing": ["is_ciio"]})]
        )
        dumped = decision.model_dump_json()
        reloaded = LegalControlDecision.model_validate_json(dumped)
        assert reloaded == decision
