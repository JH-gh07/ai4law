"""CN Transfer Diagnosis 控制平面适配器（task073 T03-T05）。

把 G1（事实完整性）、G2（规则优先级）封装为纯函数，由
``DiagnosisService.evaluate(..., control=True)`` opt-in 调用；
G4 用 ``merge_gate_results`` 按显式优先级合并。
"""
from __future__ import annotations

from backend.common.legal_control.contracts import (
    ACTION_HUMAN_REVIEW,
    ACTION_LOCK_DETERMINISTIC_PATH,
    ACTION_PROVIDE_MISSING_FACTS,
    ACTION_RESOLVE_FACT_CONFLICT,
    LegalControlDecision,
    LegalControlGateResult,
    merge_gate_results,
)
from backend.common.legal_control.trace import record_gate_trace
from backend.common.trace.recorder import TraceRecorder
from backend.domains.cn.transfer_diagnosis.models import (
    DiagnosisFacts,
    FactSource,
)
from backend.domains.cn.transfer_diagnosis.rule_engine import RuleMatch
from backend.domains.cn.transfer_diagnosis.schema import DiagnosisResult

# G1 关注的关键事实（missing_facts 只产出这三个字段的 unknown）。
CRITICAL_FACTS = ("is_ciio", "contains_important_data", "no_personal_info")

_CLARIFICATION_TEMPLATES = {
    "is_ciio": "请确认企业是否为关键信息基础设施运营者（CIIO）。",
    "contains_important_data": "请确认本次出境是否向境外提供重要数据。",
    "no_personal_info": "请确认出境数据是否不含个人信息且不涉及重要数据。",
}

# 决定性推断来源：非用户明确提供、非确定性规则确定。
_INFERRED_SOURCES = {FactSource.LLM_INFERENCE, FactSource.ESTIMATE, FactSource.DEFAULT}

_CONDITION_TO_FACT = {
    "q1_is_ciio": "is_ciio",
    "q2_has_important_data": "contains_important_data",
    "q3_pii_count_gte": "personal_info_count",
    "q3_pii_count_lt": "personal_info_count",
    "q4_spi_count_gte": "sensitive_personal_info_count",
    "q4_spi_count_lt": "sensitive_personal_info_count",
    "q5_no_personal_info": "no_personal_info",
    "q6_scenario": "transfer_scenario",
    "q7_receiver_type": "receiver_type",
}


def build_fact_completeness_gate(
    *,
    facts: DiagnosisFacts,
    validation_result: DiagnosisResult | None,
    clarification_questions: list[str],
) -> LegalControlGateResult:
    """G1 — 事实完整性门。

    - 关键事实缺失（critical missing）→ ``ESCALATE`` + ``details.critical_missing``
      （合并映射为 NEEDS_CLARIFICATION）。
    - 既有事实冲突 → ``ESCALATE`` + ``details.conflicts``（合并映射为 NEEDS_REVIEW）。
    """
    critical_missing = [f for f in facts.missing_facts if f in CRITICAL_FACTS]
    if critical_missing:
        for field in critical_missing:
            question = _CLARIFICATION_TEMPLATES.get(field)
            if question and question not in clarification_questions:
                clarification_questions.append(question)
        return LegalControlGateResult(
            gate="FACT_COMPLETENESS",
            outcome="ESCALATE",
            reasons=[f"关键事实缺失：{', '.join(critical_missing)}。"],
            refs=list(critical_missing),
            required_actions=[ACTION_PROVIDE_MISSING_FACTS],
            details={"critical_missing": critical_missing},
        )

    if validation_result is not None:
        conflicts = list(validation_result.uncertainty_notes or [])
        return LegalControlGateResult(
            gate="FACT_COMPLETENESS",
            outcome="ESCALATE",
            reasons=conflicts,
            refs=[],
            required_actions=[ACTION_RESOLVE_FACT_CONFLICT],
            details={"conflicts": conflicts},
        )

    return LegalControlGateResult(
        gate="FACT_COMPLETENESS",
        outcome="PASS",
        reasons=["关键事实已具备，无缺失或冲突。"],
    )


def build_rule_precedence_gate(
    *,
    rule_match: RuleMatch,
    facts: DiagnosisFacts,
) -> LegalControlGateResult:
    """G2 — 规则优先级门。

    - non-default 规则命中 → 锁定 canonical path（``execution_precedence=True``）。
    - 命中但决定性事实来自推断/估算/默认 → ``ESCALATE``（NEEDS_REVIEW）。
    - default 分支 → 保留 AI 推测，``execution_precedence=False``，不打确定性标签。
    """
    if rule_match.is_default:
        return LegalControlGateResult(
            gate="RULE_PRECEDENCE",
            outcome="CONDITIONAL",
            reasons=["未命中确定性规则，保留 AI 推测/默认路径，不打确定性标签。"],
            details={"execution_precedence": False},
        )

    decisive_facts = {
        _CONDITION_TO_FACT[field]
        for field in rule_match.condition_fields
        if field in _CONDITION_TO_FACT
    }
    inferred_decisive = sorted(
        field for field in decisive_facts if facts.source_for(field) in _INFERRED_SOURCES
    )
    if inferred_decisive:
        return LegalControlGateResult(
            gate="RULE_PRECEDENCE",
            outcome="ESCALATE",
            reasons=[
                "规则命中依赖推断、估算或默认事实："
                + "、".join(inferred_decisive)
                + "。"
            ],
            refs=list(inferred_decisive),
            required_actions=[ACTION_HUMAN_REVIEW],
            details={
                "execution_precedence": True,
                "decisive_inferred": inferred_decisive,
            },
        )

    return LegalControlGateResult(
        gate="RULE_PRECEDENCE",
        outcome="PASS",
        reasons=["确定性规则命中，推荐路径已锁定。"],
        required_actions=[ACTION_LOCK_DETERMINISTIC_PATH],
        details={"execution_precedence": True, "rule_id": rule_match.rule_id},
    )


def build_control_decision(
    *,
    gate_results: list[LegalControlGateResult],
    trace: TraceRecorder | None,
) -> LegalControlDecision:
    """G4 — 逐门写控制 trace，并按显式优先级合并。"""
    for gate_result in gate_results:
        record_gate_trace(trace, gate_result)
    return merge_gate_results(gate_results)
