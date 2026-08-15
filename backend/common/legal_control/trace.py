"""Legal Agent Control Plane — trace 集成（task073 T02）。

复用 ``TraceRecorder.record``，不扩展 SSE event union：控制事件以既有
``intermediate``（正常/pass）或 ``warning``（review/limitation）作为 event type，
``raw_name`` 使用 ``control.*`` 命名空间，供前端 ``trace-adapter.ts`` 识别。

只记录 gate/outcome/reasons/refs 摘要，不写敏感正文（task073 §6）。
"""
from __future__ import annotations

from typing import Any

from backend.common.legal_control.contracts import LegalControlGateResult

_GATE_TO_TRACE_NAME: dict[str, str] = {
    "FACT_COMPLETENESS": "control.fact_completeness",
    "RULE_PRECEDENCE": "control.rule_precedence",
    "EVIDENCE_SUFFICIENCY": "control.evidence_sufficiency",
    "CITATION_VALIDITY": "control.citation_validity",
    "ESCALATION": "control.escalation",
}


def gate_trace_name(gate: str) -> str:
    """返回 gate 对应的 ``control.*`` raw_name（未知 gate 回退为 ``control.gate``）。"""
    return _GATE_TO_TRACE_NAME.get(gate, f"control.{gate.lower()}")


def record_gate_trace(
    trace: Any | None,
    gate_result: LegalControlGateResult,
) -> None:
    """把单个 Gate 结果写入 trace（event type 由 outcome 决定）。

    - PASS / CONDITIONAL → ``intermediate``
    - ESCALATE / BLOCK   → ``warning``
    """
    if trace is None:
        return
    review_level = gate_result.outcome in {"ESCALATE", "BLOCK"}
    event_type = "warning" if review_level else "intermediate"
    trace.record(
        event_type,
        {
            "summary": f"控制门 {gate_result.gate}：{gate_result.outcome}",
            "detail": {
                "raw_name": gate_trace_name(gate_result.gate),
                "gate": gate_result.gate,
                "outcome": gate_result.outcome,
                "reasons": list(gate_result.reasons),
                "refs": list(gate_result.refs),
            },
        },
    )
