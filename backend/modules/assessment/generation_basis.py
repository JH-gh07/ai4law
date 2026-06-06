from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.modules.assessment.schema import RegulationHit


CHAPTER_ID_TO_TITLE = {
    "overview": "出境活动概述",
    "data_scope": "数据类型与规模",
    "necessity_legal_basis": "出境必要性与合法性基础",
    "recipient_capability": "境外接收方保障能力",
    "rights_impact": "个人信息权益影响分析",
    "security_measures": "安全措施与传输机制",
    "risk_remediation": "剩余风险与整改建议",
    "conclusion": "综合评估结论",
}


def _fact_summary(fact: FactItem) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "source_type": fact.source_type,
        "source_ref": fact.source_ref,
        "field_path": fact.field_path,
        "value": fact.normalized_value if fact.normalized_value is not None else fact.value,
        "confidence": fact.confidence,
        "notes": fact.notes,
    }


def _regulation_summary(hit: RegulationHit) -> dict[str, str]:
    return {
        "rule_id": hit.source_id,
        "title": hit.title,
        "article": hit.article,
        "snippet": hit.snippet,
    }


def _issue_summary(issue: IssueItem) -> dict[str, Any]:
    return {
        "issue_id": issue.issue_id,
        "title": issue.title,
        "description": issue.description,
        "category": issue.category,
        "severity": issue.severity,
        "fact_refs": issue.fact_refs,
        "rule_refs": issue.rule_refs,
        "evidence_refs": issue.evidence_refs,
        "recommended_action": issue.recommended_action,
    }


def _issue_grounding_items(issue_ids: list[str], legal_grounding: dict[str, Any] | None) -> list[dict[str, Any]]:
    by_issue = (legal_grounding or {}).get("by_issue", {})
    items: list[dict[str, Any]] = []
    for issue_id in issue_ids:
        issue_items = by_issue.get(issue_id, [])
        if isinstance(issue_items, list):
            items.extend(item for item in issue_items if isinstance(item, dict))
    return items


def _strategy_items(issue_ids: list[str], writing_strategy: dict[str, Any] | None) -> list[dict[str, Any]]:
    strategies = (writing_strategy or {}).get("strategies", [])
    if not isinstance(strategies, list):
        return []
    issue_id_set = set(issue_ids)
    return [
        item
        for item in strategies
        if isinstance(item, dict) and item.get("issue_id") in issue_id_set
    ]


def _evidence_summary(evidence: EvidenceItem) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "claim": evidence.claim,
        "fact_refs": evidence.fact_refs,
        "rule_refs": evidence.rule_refs,
        "conclusion": evidence.conclusion,
        "confidence": evidence.confidence,
        "used_by": evidence.used_by,
    }


def build_generation_basis_pack(
    *,
    task_id: str,
    facts: list[FactItem],
    issues: list[IssueItem],
    evidence_chain: list[EvidenceItem],
    regulations: list[RegulationHit],
    attachment_notes: list[dict[str, str]],
    path_warning: str | None,
    legal_grounding: dict[str, Any] | None = None,
    writing_strategy: dict[str, Any] | None = None,
    workflow_rules: list[dict[str, Any]] | None = None,
    template_context: list[dict[str, Any]] | None = None,
    compliance_reasoning: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the audit pack explaining what the generator is allowed to rely on."""

    facts_by_id = {fact.fact_id: fact for fact in facts}
    evidence_by_id = {evidence.evidence_id: evidence for evidence in evidence_chain}
    regulations_by_id = {hit.source_id: hit for hit in regulations}
    section_issues: dict[str, list[IssueItem]] = defaultdict(list)
    for issue in issues:
        targets = issue.affects_outputs or ["risk_remediation"]
        for target in targets:
            section_issues[target].append(issue)

    section_packs: list[dict[str, Any]] = []
    for section_id, section_title in CHAPTER_ID_TO_TITLE.items():
        related_issues = section_issues.get(section_id, [])
        related_issue_ids = [issue.issue_id for issue in related_issues]
        fact_refs = {
            fact_ref
            for issue in related_issues
            for fact_ref in issue.fact_refs
            if fact_ref in facts_by_id
        }
        evidence_refs = {
            evidence_ref
            for issue in related_issues
            for evidence_ref in issue.evidence_refs
            if evidence_ref in evidence_by_id
        }
        rule_refs = {
            rule_ref
            for issue in related_issues
            for rule_ref in issue.rule_refs
            if rule_ref in regulations_by_id
        }
        section_packs.append(
            {
                "section_id": section_id,
                "section_title": section_title,
                "confirmed_facts": [_fact_summary(facts_by_id[ref]) for ref in sorted(fact_refs)],
                "issues": [_issue_summary(issue) for issue in related_issues],
                "legal_basis": [_regulation_summary(regulations_by_id[ref]) for ref in sorted(rule_refs)],
                "legal_grounding": _issue_grounding_items(related_issue_ids, legal_grounding),
                "writing_strategy_refs": related_issue_ids,
                "writing_strategies": _strategy_items(related_issue_ids, writing_strategy),
                "evidence_refs": sorted(evidence_refs),
                "missing_materials": [
                    issue.recommended_action
                    for issue in related_issues
                    if issue.category == "documentation"
                ],
            }
        )

    return {
        "task_id": task_id,
        "module": "assessment",
        "path_warning": path_warning,
        "user_facts": [_fact_summary(fact) for fact in facts],
        "regulations": [_regulation_summary(hit) for hit in regulations],
        "workflow_rules": list(workflow_rules or []),
        "issues": [_issue_summary(issue) for issue in issues],
        "evidence_chain": [_evidence_summary(evidence) for evidence in evidence_chain],
        "legal_grounding": legal_grounding or {"by_issue": {}},
        "writing_strategy": writing_strategy or {"strategies": []},
        "compliance_reasoning": list(compliance_reasoning or []),
        "attachment_summaries": list(attachment_notes),
        "template_context": list(template_context or []),
        "section_packs": section_packs,
    }
