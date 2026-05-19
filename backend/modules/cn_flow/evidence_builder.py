from __future__ import annotations

import re

from backend.common.workflow import EvidenceItem, FactItem, IssueItem


def _evidence_id(issue_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", issue_id).strip("-")
    return f"EVIDENCE-{safe}"


def build_cn_flow_evidence(
    facts: list[FactItem],
    issues: list[IssueItem],
    regulations: list[dict],
) -> tuple[list[IssueItem], list[EvidenceItem]]:
    fact_ids = {fact.fact_id for fact in facts}
    default_rule_refs = [item.get("source_id", "") for item in regulations if item.get("source_id")]
    updated_issues: list[IssueItem] = []
    evidence_chain: list[EvidenceItem] = []

    for issue in issues:
        fact_refs = [item for item in issue.fact_refs if item in fact_ids]
        if not fact_refs:
            updated_issues.append(issue)
            continue
        evidence_id = _evidence_id(issue.issue_id)
        rule_refs = issue.rule_refs or default_rule_refs[:2]
        evidence_chain.append(
            EvidenceItem(
                evidence_id=evidence_id,
                claim=issue.title,
                fact_refs=fact_refs,
                rule_refs=rule_refs,
                conclusion=issue.recommended_action,
                confidence=0.9 if issue.severity in {"HIGH", "BLOCKER"} else 0.75,
                used_by=[issue.issue_id, *issue.affects_outputs],
            )
        )
        updated_issues.append(issue.model_copy(update={"evidence_refs": [evidence_id]}))

    return updated_issues, evidence_chain
