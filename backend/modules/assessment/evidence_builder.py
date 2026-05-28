from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.modules.assessment.schema import RegulationHit

_MATERIAL_ISSUE_IDS = {"ISSUE-missing-attachments", "ISSUE-attachments-not-parsed"}


_EVIDENCE_WORDING: dict[str, tuple[str, str]] = {
    "ISSUE-ciio-security-assessment": (
        "CIIO 事实触发安全评估路径判断",
        "企业被标记为 CIIO，应按安全评估路径准备申报和自评估材料。",
    ),
    "ISSUE-important-data": (
        "重要数据事实触发安全评估路径判断",
        "本次出境涉及重要数据，应按安全评估高风险口径处理。",
    ),
    "ISSUE-pii-threshold": (
        "个人信息规模触发安全评估路径判断",
        "普通个人信息出境规模达到阈值，应核验统计口径并准备安全评估材料。",
    ),
    "ISSUE-spi-threshold": (
        "敏感个人信息规模触发高风险判断",
        "敏感个人信息出境规模达到阈值，应按高风险口径评估并补充单独同意等材料。",
    ),
    "ISSUE-missing-receiver-country": (
        "接收国家/地区缺失影响境外接收方风险判断",
        "缺少接收国家/地区会削弱接收方所在地法律环境和保护能力评估。",
    ),
    "ISSUE-missing-attachments": (
        "附件缺失影响材料完整性风险判断",
        "未上传申报支撑材料会削弱报告的材料审查和证据追溯能力。",
    ),
    "ISSUE-attachments-not-parsed": (
        "附件摘要缺失影响材料完整性风险判断",
        "已提供附件路径但未形成解析摘要，需补充可用于报告的附件审查结果。",
    ),
}


def _diagnosis_value(diagnosis_result: object | None, field: str) -> Any:
    if diagnosis_result is None:
        return None
    if isinstance(diagnosis_result, dict):
        return diagnosis_result.get(field)
    return getattr(diagnosis_result, field, None)


def _diagnosis_rule_ref(diagnosis_result: object | None) -> str:
    matched_rule_id = _diagnosis_value(diagnosis_result, "matched_rule_id")
    if matched_rule_id:
        return f"diagnosis:{matched_rule_id}"
    recommended_path = _diagnosis_value(diagnosis_result, "recommended_path") or "unknown"
    return f"diagnosis:{recommended_path}"


def _evidence_id(issue_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", issue_id.removeprefix("ISSUE-")).strip("-")
    return f"EVIDENCE-{safe}"


def _regulation_rule_refs(regulations: list[RegulationHit]) -> list[str]:
    return [item.source_id for item in regulations if item.source_id]


def _confidence(severity: str, has_rule_refs: bool) -> float:
    if severity in {"HIGH", "BLOCKER"} and has_rule_refs:
        return 0.9
    if severity in {"HIGH", "BLOCKER"}:
        return 0.8
    if severity == "MEDIUM":
        return 0.75
    return 0.6


def _rule_refs_for_issue(
    issue: IssueItem,
    regulations: list[RegulationHit],
    diagnosis_result: object | None,
) -> list[str]:
    if issue.rule_refs:
        return list(issue.rule_refs)
    if issue.issue_id in _MATERIAL_ISSUE_IDS:
        return []
    regulation_refs = _regulation_rule_refs(regulations)
    if regulation_refs:
        return regulation_refs[:3]
    return [_diagnosis_rule_ref(diagnosis_result)]


def build_assessment_evidence(
    facts: list[FactItem],
    issues: list[IssueItem],
    regulations: list[RegulationHit],
    diagnosis_result: object | None,
) -> tuple[list[IssueItem], list[EvidenceItem]]:
    fact_ids = {fact.fact_id for fact in facts}
    evidence_chain: list[EvidenceItem] = []
    updated_issues: list[IssueItem] = []

    for issue in issues:
        fact_refs = [fact_ref for fact_ref in issue.fact_refs if fact_ref in fact_ids]
        if not fact_refs:
            updated_issues.append(issue)
            continue

        evidence_id = _evidence_id(issue.issue_id)
        claim, conclusion = _EVIDENCE_WORDING.get(
            issue.issue_id,
            (issue.title, issue.recommended_action),
        )
        rule_refs = _rule_refs_for_issue(issue, regulations, diagnosis_result)
        evidence = EvidenceItem(
            evidence_id=evidence_id,
            claim=claim,
            fact_refs=fact_refs,
            rule_refs=rule_refs,
            conclusion=conclusion,
            confidence=_confidence(issue.severity, bool(rule_refs)),
            used_by=[issue.issue_id, *issue.affects_outputs],
        )
        evidence_chain.append(evidence)
        updated_issues.append(issue.model_copy(update={"evidence_refs": [evidence_id]}))

    return updated_issues, evidence_chain
