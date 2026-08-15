"""task073 T08 — ESCALATION 门（repair_blocked / 未解决 blocking）单元测试。"""
from __future__ import annotations

from backend.domains.cn.security_assessment.escalation_gate import run_escalation_gate


def test_no_runtime_blockers_passes():
    gate = run_escalation_gate(consistency_issues=[])
    assert gate.gate == "ESCALATION"
    assert gate.outcome == "PASS"


def test_repair_blocked_flag_escalates():
    gate = run_escalation_gate(repair_blocked=True, consistency_issues=["REPAIR_BLOCKED: x"])
    assert gate.outcome == "ESCALATE"
    assert gate.details["repair_blocked"] is True


def test_repair_blocked_sentinel_escalates():
    gate = run_escalation_gate(
        consistency_issues=["REPAIR_BLOCKED: 存在无法自动修复的一致性问题。"]
    )
    assert gate.outcome == "ESCALATE"


def test_unresolved_blocking_issue_escalates():
    gate = run_escalation_gate(
        consistency_issues=["Issue ISSUE-1 references missing facts: FACT-X."]
    )
    assert gate.outcome == "ESCALATE"
    assert "references missing facts" in gate.reasons[0]


def test_non_blocking_remaining_issue_does_not_escalate():
    # 非 blocking 的残余 issue（已尝试修复但非阻断类）不应触发 ESCALATE。
    gate = run_escalation_gate(
        consistency_issues=["Chapter 1 has no citation."]
    )
    assert gate.outcome == "PASS"
