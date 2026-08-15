"""Legal Agent Control Plane（task073）。

轻量控制平面契约与聚合逻辑。所有控制逻辑 opt-in；未传 ``control`` 时，
Domain Workflow 的输出、事件顺序和异常语义保持不变。
"""
from backend.common.legal_control.contracts import (
    ACTION_HUMAN_REVIEW,
    ACTION_LOCK_DETERMINISTIC_PATH,
    ACTION_PROVIDE_MISSING_FACTS,
    ACTION_RESOLVE_FACT_CONFLICT,
    ACTION_SUPPLEMENT_EVIDENCE,
    ACTION_VERIFY_SOURCE_IDENTITY,
    GateName,
    GateOutcome,
    LegalControlDecision,
    LegalControlGateResult,
    LegalControlStatus,
    merge_gate_results,
)
from backend.common.legal_control.trace import (
    gate_trace_name,
    record_gate_trace,
)

__all__ = [
    "ACTION_HUMAN_REVIEW",
    "ACTION_LOCK_DETERMINISTIC_PATH",
    "ACTION_PROVIDE_MISSING_FACTS",
    "ACTION_RESOLVE_FACT_CONFLICT",
    "ACTION_SUPPLEMENT_EVIDENCE",
    "ACTION_VERIFY_SOURCE_IDENTITY",
    "GateName",
    "GateOutcome",
    "LegalControlDecision",
    "LegalControlGateResult",
    "LegalControlStatus",
    "gate_trace_name",
    "merge_gate_results",
    "record_gate_trace",
]
