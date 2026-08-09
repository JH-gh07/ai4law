"""DPIA generation basis pack — per-section facts, issues, legal grounding, and writing strategies.

Organizes all pipeline outputs into section packs aligned with the 7 DPIA template sections
(ICO DPIA template / GDPR Art 35 requirements).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.domains.eu.dpia.schema import RegulationHit


DPIA_CHAPTER_ID_TO_TITLE: dict[str, str] = {
    "need_identification": "1. 识别需求 (Identify Need for DPIA)",
    "processing_description": "2. 描述处理活动 (Describe the Processing)",
    "consultation": "3. 咨询过程 (Consultation Process)",
    "necessity_proportionality": "4. 必要性与相称性 (Necessity & Proportionality)",
    "risk_assessment": "5. 风险识别与评估 (Identify & Assess Risks)",
    "mitigation": "6. 降低风险的措施 (Mitigation Measures)",
    "signoff": "7. 签署与记录 (Sign Off & Record Outcomes)",
}

DPIA_CHAPTER_KEYS = list(DPIA_CHAPTER_ID_TO_TITLE.keys())

# Facts required by a chapter even when no issue points at them. Issue-driven
# routing alone left consultation empty and omitted lawful-basis facts from the
# necessity chapter, which made the model contradict known request data.
_SECTION_FACT_PATH_PREFIXES: dict[str, tuple[str, ...]] = {
    "need_identification": (
        "dpia.project_name",
        "dpia.project_goal",
        "dpia_need.",
    ),
    "processing_description": (
        "dpia.processing_flow_description",
        "dpia.data_categories",
        "dpia.data_subject_",
        "dpia.retention_period",
        "dpia.cross_border_transfer",
        "dpia.transfer_destination",
        "dpia.automated_decision_making",
        "dpia.systematic_monitoring",
        "dpia.large_scale_processing",
        "dpia.data_matching",
        "dpia.new_technology",
    ),
    "consultation": (
        "dpia.consulted_internal_departments",
        "dpia.external_experts",
        "dpia.data_subject_consultation_plan",
        "dpia.dpo_name",
        "dpia.dpo_opinion",
    ),
    "necessity_proportionality": (
        "dpia.lawful_basis",
        "dpia.necessity_statement",
        "dpia.proportionality_statement",
        "dpia.transparency_information",
        "dpia.special_category_",
    ),
    "risk_assessment": (
        "dpia.identified_risks.",
        "dpia.automated_decision_making",
        "dpia.large_scale_processing",
        "dpia.new_technology",
        "dpia.vulnerable_data_subjects",
    ),
    "mitigation": ("dpia.mitigation_measures.",),
    "signoff": (
        "dpia.dpia_owner",
        "dpia.dpo_name",
        "dpia.dpo_opinion",
        "dpia.review_date",
        "dpia_need.prior_consultation_possible",
    ),
}


def _is_section_fact(section_id: str, fact: FactItem) -> bool:
    path = fact.field_path or ""
    return any(
        path == prefix or (prefix.endswith(".") and path.startswith(prefix))
        for prefix in _SECTION_FACT_PATH_PREFIXES.get(section_id, ())
    )


def _fact_summary(fact: FactItem) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "source_type": fact.source_type,
        "source_ref": fact.source_ref,
        "field_path": fact.field_path,
        "value": fact.normalized_value if fact.normalized_value is not None else fact.value,
        "confidence": fact.confidence,
        "evidence_status": fact.evidence_status,
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


def _issue_grounding_items(
    issue_ids: list[str], legal_grounding: dict[str, Any] | None
) -> list[dict[str, Any]]:
    by_issue = (legal_grounding or {}).get("by_issue", {})
    items: list[dict[str, Any]] = []
    for issue_id in issue_ids:
        issue_items = by_issue.get(issue_id, [])
        if isinstance(issue_items, list):
            items.extend(item for item in issue_items if isinstance(item, dict))
    return items


def _strategy_items(
    issue_ids: list[str], writing_strategy: dict[str, Any] | None
) -> list[dict[str, Any]]:
    strategies = (writing_strategy or {}).get("strategies", [])
    if not isinstance(strategies, list):
        return []
    issue_id_set = set(issue_ids)
    return [item for item in strategies if isinstance(item, dict) and item.get("issue_id") in issue_id_set]


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
    need_assessment: dict[str, Any] | None = None,
    legal_grounding: dict[str, Any] | None = None,
    writing_strategy: dict[str, Any] | None = None,
    risk_matrix: list[dict[str, Any]] | None = None,
    mitigation_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the DPIA generation basis pack.

    Organizes facts, issues, evidence, regulations, and strategies into
    per-section packs aligned with the 7 DPIA template sections.
    """
    facts_by_id = {fact.fact_id: fact for fact in facts}
    evidence_by_id = {evidence.evidence_id: evidence for evidence in evidence_chain}
    regulations_by_id = {hit.source_id: hit for hit in regulations}
    section_issues: dict[str, list[IssueItem]] = defaultdict(list)
    for issue in issues:
        targets = issue.affects_outputs or ["risk_assessment"]
        for target in targets:
            section_issues[target].append(issue)

    section_packs: list[dict[str, Any]] = []
    for section_id, section_title in DPIA_CHAPTER_ID_TO_TITLE.items():
        related_issues = section_issues.get(section_id, [])
        related_issue_ids = [issue.issue_id for issue in related_issues]
        fact_refs = {
            fact_ref
            for issue in related_issues
            for fact_ref in issue.fact_refs
            if fact_ref in facts_by_id
        }
        fact_refs.update(
            fact.fact_id for fact in facts if _is_section_fact(section_id, fact)
        )
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
        section_packs.append({
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
                if issue.category in {"documentation", "mitigation_gap"}
            ],
        })

    return {
        "task_id": task_id,
        "module": "dpia",
        "need_assessment": need_assessment,
        "user_facts": [_fact_summary(fact) for fact in facts],
        "regulations": [_regulation_summary(hit) for hit in regulations],
        "issues": [_issue_summary(issue) for issue in issues],
        "evidence_chain": [_evidence_summary(ev) for ev in evidence_chain],
        "legal_grounding": legal_grounding or {"by_issue": {}},
        "writing_strategy": writing_strategy or {"strategies": []},
        "attachment_summaries": list(attachment_notes),
        "risk_matrix": risk_matrix or [],
        "mitigation_plan": mitigation_plan or [],
        "section_packs": section_packs,
    }
