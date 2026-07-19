from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.domains.cn.security_assessment.schema import RegulationHit

_MATERIAL_ISSUE_IDS = {
    "ISSUE-missing-attachments",
    "ISSUE-attachments-not-parsed",
    "ISSUE-material-checklist-incomplete",
    "ISSUE-internal-approval-missing",
}


_EVIDENCE_WORDING: dict[str, tuple[str, str]] = {
    "ISSUE-recommended-path-mismatch": (
        "诊断路径与安全评估报告不匹配",
        "诊断模块推荐路径与当前生成的安全评估报告不一致，需标注为强制生成的参考草案。",
    ),
    "ISSUE-ciio-security-assessment": (
        "CIIO 事实触发安全评估路径判断",
        "企业被标记为 CIIO，应按安全评估路径准备申报和自评估材料。",
    ),
    "ISSUE-important-data-security-assessment": (
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
    "ISSUE-missing-transfer-purpose": (
        "出境目的不明确影响必要性和合法性分析",
        "未提供清晰的出境目的，无法充分论证出境活动的必要性和合法性基础。",
    ),
    "ISSUE-spi-classification-uncertain": (
        "敏感个人信息定性需进一步确认",
        "存在敏感个人信息出境但未提供具体敏感类型清单和分类依据。",
    ),
    "ISSUE-necessity-argument-generic": (
        "出境必要性论证可能过于泛化",
        "当前出境目的描述可能不足以支撑严格的必要性审查。",
    ),
    "ISSUE-recipient-security-evidence-missing": (
        "境外接收方安全保障能力证明不足",
        "当前材料对境外接收方的数据安全管理制度、认证证明或第三方审计材料描述不足。",
    ),
    "ISSUE-legal-document-gaps": (
        "法律文件核心条款可能存在缺失",
        "与境外接收方签署的法律文件未验证是否包含六项核心条款。",
    ),
    "ISSUE-onward-transfer-unclear": (
        "再转移约束条款不明确",
        "未验证法律文件是否明确约束境外接收方不得将数据再转移至第三方。",
    ),
    "ISSUE-consent-evidence-missing": (
        "个人信息出境单独同意记录证据不足",
        "涉及个人信息出境时未验证是否已取得个人信息主体的单独同意及同意记录。",
    ),
    "ISSUE-anonymization-uncertain": (
        "匿名化或去标识化有效性未验证",
        "如拟主张数据已匿名化或去标识化，需补充技术验证、重识别风险评估或第三方审计材料。",
    ),
    "ISSUE-material-checklist-incomplete": (
        "申报支撑材料清单不完整",
        "当前仅根据输入字段推断材料需求，未基于完整申报材料清单逐项核验。",
    ),
    "ISSUE-internal-approval-missing": (
        "内部审批和数据出境监控机制未体现",
        "未体现企业内部数据出境审批流程、定期监控机制和责任人信息。",
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
