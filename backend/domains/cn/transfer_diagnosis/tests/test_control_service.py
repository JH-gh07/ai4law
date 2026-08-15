"""task073 T03-T05 — Diagnosis 控制门 service 级验收（D1-D6）。"""
from __future__ import annotations

import json

from backend.common.trace.recorder import TraceRecorder
from backend.domains.cn.transfer_diagnosis.schema import DiagnosisAnswers, YesNoUnknown
from backend.domains.cn.transfer_diagnosis.service import DiagnosisService


def _read_events(trace_dir):
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(trace_dir.glob("*.json"))
    ]


# ── D1：完整 non-default ────────────────────────────────────────────────

def test_d1_complete_non_default_is_auto():
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.NO,
        q3_pii_count=1_100_000,
        q4_spi_count=200,
        q8_purpose="marketing analytics",
    )
    baseline = service.evaluate(answers)
    result = service.evaluate(answers, control=True)

    assert result.recommended_path == baseline.recommended_path == "security_assessment"
    assert result.matched_rule_id == "pii_threshold"
    assert result.control_decision is not None
    assert result.control_decision.legal_control_status == "AUTO"
    assert result.clarification_questions == []


# ── D2：critical missing ────────────────────────────────────────────────

def test_d2_critical_missing_needs_clarification():
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.UNKNOWN,
        q2_has_important_data=YesNoUnknown.NO,
        q3_pii_count=0,
        q4_spi_count=0,
        q5_no_personal_info=YesNoUnknown.NO,
    )
    result = service.evaluate(answers, control=True)

    assert result.control_decision.legal_control_status == "NEEDS_CLARIFICATION"
    assert result.clarification_questions
    assert result.control_decision.gate_results[0].gate == "FACT_COMPLETENESS"
    assert result.control_decision.gate_results[0].details["critical_missing"] == ["is_ciio"]


# ── D3：既有冲突 ────────────────────────────────────────────────────────

def test_d3_conflict_keeps_manual_review_and_needs_review():
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.YES,
        q3_pii_count=0,
        q4_spi_count=0,
        q5_no_personal_info=YesNoUnknown.YES,
    )
    result = service.evaluate(answers, control=True)

    assert result.recommended_path == "manual_review"
    assert result.conclusion_source == "validation"
    assert result.requires_human_review is True
    assert result.control_decision.legal_control_status == "NEEDS_REVIEW"


# ── D4：decisive inference（LLM_INFERENCE / ESTIMATE） ─────────────────

def test_d4_llm_inference_decisive_fact_needs_review(monkeypatch):
    service = DiagnosisService()
    monkeypatch.setattr(
        service.agents["important_data"],
        "run",
        lambda **_: {
            "result": "可能涉及重要数据",
            "confidence": 0.8,
            "suggested_answer": "yes",
        },
    )
    result = service.evaluate(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.UNKNOWN,
            q3_pii_count=0,
            q4_spi_count=0,
            q5_no_personal_info=YesNoUnknown.NO,
        ),
        control=True,
    )
    assert result.matched_rule_id == "important_data"
    assert result.control_decision.legal_control_status == "NEEDS_REVIEW"


def test_d4_estimate_decisive_fact_needs_review():
    service = DiagnosisService()
    result = service.evaluate(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.NO,
            q3_pii_count=0,
            q4_spi_count=0,
            m3_processes_personal_info="yes",
            m3_data_volume_range="100-1000万条",
        ),
        control=True,
    )
    assert result.matched_rule_id == "pii_threshold"
    assert result.control_decision.legal_control_status == "NEEDS_REVIEW"


# ── D5：default → AI ────────────────────────────────────────────────────

def test_d5_default_to_ai_keeps_inference_unlocked():
    service = DiagnosisService()
    result = service.evaluate(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.NO,
            q3_pii_count=0,
            q4_spi_count=0,
            q5_no_personal_info=YesNoUnknown.NO,
        ),
        control=True,
    )
    assert result.control_decision.legal_control_status == "CONDITIONAL"
    rule_gate = next(
        g for g in result.control_decision.gate_results if g.gate == "RULE_PRECEDENCE"
    )
    assert rule_gate.details["execution_precedence"] is False
    assert result.conclusion_source != "rule"
    assert result.matched_rule_id is None


# ── D6：default-off（未传 control） ─────────────────────────────────────

def test_d6_default_off_has_no_control_fields():
    service = DiagnosisService()
    answers = DiagnosisAnswers(
        q1_is_ciio=YesNoUnknown.NO,
        q2_has_important_data=YesNoUnknown.NO,
        q3_pii_count=1_100_000,
        q4_spi_count=200,
    )
    result = service.evaluate(answers)
    assert result.control_decision is None
    assert result.clarification_questions == []


# ── trace：控制门事件写入，且不改变既有事件顺序 ──────────────────────────

def test_control_trace_written_and_order_preserved(tmp_path):
    service = DiagnosisService()
    recorder = TraceRecorder(tmp_path, task_id="task-d")
    result = service.evaluate(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.NO,
            q3_pii_count=1_100_000,
            q4_spi_count=200,
        ),
        trace=recorder,
        control=True,
    )
    assert result.control_decision is not None
    events = _read_events(tmp_path)
    control_events = [
        e for e in events
        if str(e["payload"].get("detail", {}).get("raw_name", "")).startswith("control.")
    ]
    assert len(control_events) == 2  # G1 + G2
    names = [e["name"] for e in events]
    assert names[0] == "status"  # 既有开始事件仍最先
    assert names[-1] == "final"  # 既有结束事件仍最后
    for ce in control_events:
        detail = ce["payload"]["detail"]
        assert detail["gate"] in {"FACT_COMPLETENESS", "RULE_PRECEDENCE"}
        assert detail["outcome"] in {"PASS", "CONDITIONAL", "ESCALATE", "BLOCK"}
