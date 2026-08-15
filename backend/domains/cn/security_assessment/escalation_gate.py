"""CN Security Assessment — Escalation 门（task073 T08）。

在 repair 之后聚合**运行时阻断信号**（Evidence/Citation 门不覆盖的信号）：
- ``repair_blocked``：repair 后仍存在无法自动修复的 blocking 一致性问题；
- 既有 consistency / alignment 未解决（blocking 类）。

输出 ``ESCALATION`` 门结果。正常/PASS 不触发升级；blocking 未解决 →
ESCALATE（NEEDS_REVIEW）。``BLOCKED`` 保留契约，pilot 不主动触发。
"""
from __future__ import annotations

from backend.common.legal_control.contracts import (
    ACTION_HUMAN_REVIEW,
    LegalControlGateResult,
)

# 与 repair_generator._BLOCKING_PATTERNS 对应的可见信号（只读判定，
# 不复制修复逻辑；repair 无法自动修复的问题会以这些短语留在最终 issues 中）。
_BLOCKING_SIGNALS = (
    "references missing facts",
    "references missing rules",
    "references missing evidence",
    "does not mention HIGH/BLOCKER issue",
    "says materials are complete",
    "denies important data",
    "leaked into external report",
)

_REPAIR_BLOCKED_SENTINEL = "REPAIR_BLOCKED:"


def run_escalation_gate(
    *,
    repair_blocked: bool = False,
    consistency_issues: list[str] | None = None,
) -> LegalControlGateResult:
    """运行时阻断聚合，输出 ESCALATION 门结果。"""
    remaining = list(consistency_issues or [])

    # 兼容：pipeline 在 repair_blocked 时把哨兵追加进 consistency_issues；
    # 若调用方直接传入 repair_blocked 也要识别。
    sentinel_present = any(_REPAIR_BLOCKED_SENTINEL in issue for issue in remaining)
    blocked = repair_blocked or sentinel_present

    if blocked:
        return LegalControlGateResult(
            gate="ESCALATION",
            outcome="ESCALATE",
            reasons=["repair 后仍存在无法自动修复的一致性问题，报告输出已被阻断。"],
            refs=sorted(
                {issue for issue in remaining if _REPAIR_BLOCKED_SENTINEL in issue}
            ),
            required_actions=[ACTION_HUMAN_REVIEW],
            details={"repair_blocked": True, "remaining_issues": remaining},
        )

    blocking = [
        issue
        for issue in remaining
        if any(signal in issue for signal in _BLOCKING_SIGNALS)
    ]
    if blocking:
        return LegalControlGateResult(
            gate="ESCALATION",
            outcome="ESCALATE",
            reasons=[
                "存在未解决的 blocking 一致性问题："
                + "；".join(blocking)
                + "。"
            ],
            refs=blocking,
            required_actions=[ACTION_HUMAN_REVIEW],
            details={"repair_blocked": False, "remaining_issues": blocking},
        )

    return LegalControlGateResult(
        gate="ESCALATION",
        outcome="PASS",
        reasons=["无运行时阻断信号，未触发人工升级。"],
        details={"repair_blocked": False, "remaining_issues": remaining},
    )
