"""Legal Agent Control Plane — 核心契约（task073 T01）。

独立命名空间，解决与 ``render_manifest.GateResult``（name/status/diagnostics）
的同名冲突：本模块的 ``LegalControlGateResult`` 使用 gate/outcome/reasons/refs/
required_actions/details，绝不从 ``render_manifest.GateResult`` 导入或复用。

字段契约冻结，变更需同步 status/todo/task073 与 OpenAPI。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GateName = Literal[
    "FACT_COMPLETENESS",
    "RULE_PRECEDENCE",
    "EVIDENCE_SUFFICIENCY",
    "CITATION_VALIDITY",
    "ESCALATION",
]

GateOutcome = Literal["PASS", "CONDITIONAL", "ESCALATE", "BLOCK"]

LegalControlStatus = Literal[
    "AUTO",
    "CONDITIONAL",
    "NEEDS_CLARIFICATION",
    "NEEDS_REVIEW",
    "BLOCKED",
]


class LegalControlGateResult(BaseModel):
    """单个控制门（Gate）的判定结果。

    ``outcome`` 表达该门的内部结论（PASS/CONDITIONAL/ESCALATE/BLOCK）；
    汇总为 ``LegalControlDecision.legal_control_status`` 时使用显式优先级，
    见 :func:`merge_gate_results`。
    """

    gate: GateName
    outcome: GateOutcome
    reasons: list[str] = Field(default_factory=list)
    refs: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class LegalControlDecision(BaseModel):
    """一次运行的最终法律自动化控制结论。

    ``legal_control_status`` 只表达法律自动化可用程度，与 ``task_status/state``
    （程序执行状态）严格分离，禁止互相映射为失败。
    """

    legal_control_status: LegalControlStatus = "AUTO"
    gate_results: list[LegalControlGateResult] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)


# ── 状态优先级（显式，禁止用字典迭代顺序或最后写入值决定） ─────────────
# 值越大优先级越高。
_STATUS_PRIORITY: dict[LegalControlStatus, int] = {
    "AUTO": 0,
    "CONDITIONAL": 1,
    "NEEDS_CLARIFICATION": 2,
    "NEEDS_REVIEW": 3,
    "BLOCKED": 4,
}

# outcome → status 的默认映射。
_OUTCOME_TO_STATUS: dict[GateOutcome, LegalControlStatus] = {
    "PASS": "AUTO",
    "CONDITIONAL": "CONDITIONAL",
    "ESCALATE": "NEEDS_REVIEW",
    "BLOCK": "BLOCKED",
}

# ── required_actions 标准常量 ────────────────────────────────────────────
ACTION_PROVIDE_MISSING_FACTS = "补充缺失的关键事实后重新运行路径判定"
ACTION_HUMAN_REVIEW = "由合规人员人工复核后确认结论"
ACTION_VERIFY_SOURCE_IDENTITY = "核实引用来源的注册身份（SourceRegistry）与允许用途"
ACTION_SUPPLEMENT_EVIDENCE = "为核心结论补充事实、规则或证据引用"
ACTION_RESOLVE_FACT_CONFLICT = "核实并消除输入事实之间的直接冲突"
ACTION_LOCK_DETERMINISTIC_PATH = "规则命中已锁定推荐路径，解释性文本不得改判"


def _higher(left: LegalControlStatus, right: LegalControlStatus) -> LegalControlStatus:
    return left if _STATUS_PRIORITY[left] >= _STATUS_PRIORITY[right] else right


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def merge_gate_results(
    gate_results: list[LegalControlGateResult],
) -> LegalControlDecision:
    """按显式优先级合并 Gate 结果，得到最终 ``LegalControlDecision``。

    规则：
    - PASS 不提升状态；CONDITIONAL→CONDITIONAL；ESCALATE→NEEDS_REVIEW；
      BLOCK→BLOCKED。
    - 特例：``FACT_COMPLETENESS`` 门判定为 ``ESCALATE`` 且 ``details`` 带
      ``critical_missing``（关键事实缺失）时，映射为 ``NEEDS_CLARIFICATION``
      （V1 中 NEEDS_CLARIFICATION 的唯一来源）。
    - 既有冲突与决定性推断由调用方以 ``ESCALATE``（不含 ``critical_missing``）
      表达，映射为 NEEDS_REVIEW。
    """
    status: LegalControlStatus = "AUTO"
    reasons: list[str] = []
    required_actions: list[str] = []

    for gr in gate_results:
        reasons.extend(gr.reasons)
        required_actions.extend(gr.required_actions)
        if (
            gr.gate == "FACT_COMPLETENESS"
            and gr.outcome == "ESCALATE"
            and gr.details.get("critical_missing")
        ):
            candidate: LegalControlStatus = "NEEDS_CLARIFICATION"
        else:
            candidate = _OUTCOME_TO_STATUS.get(gr.outcome, "AUTO")
        status = _higher(status, candidate)

    return LegalControlDecision(
        legal_control_status=status,
        gate_results=list(gate_results),
        reasons=_dedup_preserve_order(reasons),
        required_actions=_dedup_preserve_order(required_actions),
    )
