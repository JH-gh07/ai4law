"""Assessment Evidence Sufficiency Gate（task073 T06-B/T07）。

在 ``_build_context_pack`` 完成（facts/issues/evidence/legal_grounding/
CitationRegistry 齐备）后、``generate_chapters`` 前执行 E1-E5，输出
``EVIDENCE_SUFFICIENCY`` 门结果。公共 ``WorkflowPipeline`` 不改默认行为：
本门由 Assessment-specific adapter 显式调用。

E1 引用完整性：核心 Issue 的 fact/rule/evidence 引用是否齐备。
E2 法律依据存在性：核心 Issue 是否有 legal grounding（regulation/citation）。
E3 外部积极事实可支持性：可进入外部报告的核心 Issue，其事实是否可支撑积极结论。
E4 单一低置信支持：核心 Issue 仅有一份低置信证据。
E5 既有 consistency dangling refs：复用 ``check_context_pack_consistency``。
"""
from __future__ import annotations

from backend.common.legal_control.contracts import (
    ACTION_SUPPLEMENT_EVIDENCE,
    LegalControlGateResult,
)
from backend.common.workflow import GenerationContextPack, IssueItem
from backend.domains.cn.security_assessment.consistency_checker import (
    check_context_pack_consistency,
)

CORE_SEVERITIES = {"HIGH", "BLOCKER"}
LOW_CONFIDENCE_THRESHOLD = 0.65


def _legal_bindings_for(context_pack: GenerationContextPack, issue_id: str) -> list:
    grounding = context_pack.legal_grounding or {}
    by_issue = grounding.get("by_issue", {}) or {}
    return by_issue.get(issue_id, [])


def _evaluate_core_issue(
    issue: IssueItem,
    context_pack: GenerationContextPack,
    fact_by_id: dict,
    evidence_by_id: dict,
) -> dict:
    deficiencies: list[str] = []
    refs: list[str] = []

    # E1 — 引用完整性
    if not issue.fact_refs:
        deficiencies.append("no_fact_refs")
    if not issue.rule_refs:
        deficiencies.append("no_rule_refs")
    if not issue.evidence_refs:
        deficiencies.append("no_evidence_refs")

    # E2 — 法律依据存在性
    bindings = _legal_bindings_for(context_pack, issue.issue_id)
    if not bindings:
        deficiencies.append("no_legal_basis")

    # E3 — 外部积极事实可支持性
    if issue.can_enter_external_report:
        issue_facts = [fact_by_id[ref] for ref in issue.fact_refs if ref in fact_by_id]
        supportable = [fact for fact in issue_facts if fact.can_support_external_positive_claim]
        if issue_facts and not supportable:
            deficiencies.append("no_external_positive_fact_support")
            refs.extend(fact.fact_id for fact in issue_facts)

    # E4 — 单一低置信支持
    if len(issue.evidence_refs) == 1:
        evidence = evidence_by_id.get(issue.evidence_refs[0])
        if evidence is not None and evidence.confidence < LOW_CONFIDENCE_THRESHOLD:
            deficiencies.append("single_low_confidence_evidence")
            refs.append(evidence.evidence_id)

    if "no_legal_basis" in deficiencies:
        status = "UNSUPPORTED"
    elif deficiencies:
        status = "PARTIAL"
    else:
        status = "SUPPORTED"

    return {
        "issue_id": issue.issue_id,
        "severity": issue.severity,
        "status": status,
        "deficiencies": deficiencies,
        "refs": sorted(set(refs)),
    }


def run_evidence_gate(context_pack: GenerationContextPack) -> LegalControlGateResult:
    """E1-E5 证据充分性判定，输出 EVIDENCE_SUFFICIENCY 门结果。"""
    fact_by_id = {fact.fact_id: fact for fact in context_pack.facts}
    evidence_by_id = {
        evidence.evidence_id: evidence for evidence in context_pack.evidence_chain
    }
    core_issues = [
        issue for issue in context_pack.issues if issue.severity in CORE_SEVERITIES
    ]

    support_matrix: list[dict] = []
    unsupported: list[str] = []
    partial: list[str] = []
    reasons: list[str] = []
    refs: list[str] = []

    for issue in core_issues:
        entry = _evaluate_core_issue(
            issue, context_pack, fact_by_id, evidence_by_id
        )
        support_matrix.append(entry)
        if entry["status"] == "UNSUPPORTED":
            unsupported.append(issue.issue_id)
            reasons.append(
                f"核心 Issue {issue.issue_id} 缺乏法律依据或事实基础："
                + "、".join(entry["deficiencies"]) + "。"
            )
        elif entry["status"] == "PARTIAL":
            partial.append(issue.issue_id)
            reasons.append(
                f"核心 Issue {issue.issue_id} 证据不完整："
                + "、".join(entry["deficiencies"]) + "。"
            )
        refs.extend(entry["refs"])

    # E5 — 既有 consistency dangling refs（全部 issue/evidence，不止核心）
    limitations: list[dict] = []
    dangling = check_context_pack_consistency(context_pack)
    for message in dangling:
        limitations.append({"type": "DANGLING_REF", "message": message})
        reasons.append(message)

    # DOCUMENT_TRACE_GAP：document_refs=[] 只记 limitation，不 BLOCK。
    for evidence in context_pack.evidence_chain:
        if not evidence.document_refs:
            limitations.append(
                {
                    "type": "DOCUMENT_TRACE_GAP",
                    "evidence_id": evidence.evidence_id,
                    "message": f"Evidence {evidence.evidence_id} 无文档定位引用。",
                }
            )

    if unsupported:
        outcome = "ESCALATE"
    elif partial or dangling:
        outcome = "CONDITIONAL"
    else:
        outcome = "PASS"

    return LegalControlGateResult(
        gate="EVIDENCE_SUFFICIENCY",
        outcome=outcome,
        reasons=sorted(set(reasons)),
        refs=sorted(set(refs)),
        required_actions=[ACTION_SUPPLEMENT_EVIDENCE] if outcome != "PASS" else [],
        details={
            "support_matrix": support_matrix,
            "limitations": limitations,
            "core_issue_count": len(core_issues),
            "unsupported_count": len(unsupported),
            "partial_count": len(partial),
        },
    )
