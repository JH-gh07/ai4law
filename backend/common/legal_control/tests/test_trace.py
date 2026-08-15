"""task073 T02 — trace 集成测试。"""
from __future__ import annotations

import json

from backend.common.legal_control.contracts import LegalControlGateResult
from backend.common.legal_control.trace import gate_trace_name, record_gate_trace
from backend.common.trace.recorder import TraceRecorder


def _read_events(trace_dir):
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(trace_dir.glob("*.json"))
    ]


def test_gate_trace_name_mapping():
    assert gate_trace_name("FACT_COMPLETENESS") == "control.fact_completeness"
    assert gate_trace_name("RULE_PRECEDENCE") == "control.rule_precedence"
    assert gate_trace_name("EVIDENCE_SUFFICIENCY") == "control.evidence_sufficiency"
    assert gate_trace_name("CITATION_VALIDITY") == "control.citation_validity"
    assert gate_trace_name("ESCALATION") == "control.escalation"


def test_pass_gate_uses_intermediate(tmp_path):
    recorder = TraceRecorder(tmp_path, task_id="task-1")
    record_gate_trace(
        recorder,
        LegalControlGateResult(gate="RULE_PRECEDENCE", outcome="PASS"),
    )
    events = _read_events(tmp_path)
    assert len(events) == 1
    assert events[0]["name"] == "intermediate"
    assert events[0]["seq"] == 1
    detail = events[0]["payload"]["detail"]
    assert detail["raw_name"] == "control.rule_precedence"
    assert detail["gate"] == "RULE_PRECEDENCE"
    assert detail["outcome"] == "PASS"


def test_escalate_gate_uses_warning(tmp_path):
    recorder = TraceRecorder(tmp_path, task_id="task-1")
    record_gate_trace(
        recorder,
        LegalControlGateResult(
            gate="FACT_COMPLETENESS",
            outcome="ESCALATE",
            details={"critical_missing": ["is_ciio"]},
            reasons=["关键事实缺失"],
            refs=["is_ciio"],
        ),
    )
    events = _read_events(tmp_path)
    assert events[0]["name"] == "warning"
    detail = events[0]["payload"]["detail"]
    assert detail["raw_name"] == "control.fact_completeness"
    assert detail["reasons"] == ["关键事实缺失"]
    assert detail["refs"] == ["is_ciio"]


def test_existing_event_order_unchanged(tmp_path):
    """既有 status/intermediate/warning 顺序不变，控制事件只追加。"""
    recorder = TraceRecorder(tmp_path, task_id="task-1")
    recorder.record("status", {"summary": "开始"})
    record_gate_trace(
        recorder,
        LegalControlGateResult(gate="EVIDENCE_SUFFICIENCY", outcome="CONDITIONAL"),
    )
    recorder.record("warning", {"summary": "既有警告"})
    events = _read_events(tmp_path)
    assert [e["name"] for e in events] == ["status", "intermediate", "warning"]
    assert [e["seq"] for e in events] == [1, 2, 3]
