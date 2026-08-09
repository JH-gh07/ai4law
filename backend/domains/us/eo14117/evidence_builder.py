"""US 14117 evidence builder — links issues to facts and regulations."""

from __future__ import annotations

import re

from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.domains.us.eo14117.rule_engine import (
    SECTION_COVERED_PERSON,
    SECTION_PROHIBITED_DEFINITION,
    SECTION_RESTRICTED_AUTHORIZATION,
)


def _evidence_id(issue_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", issue_id).strip("-")
    return f"US14117-EVIDENCE-{safe}"


def build_us_14117_evidence(
    facts: list[FactItem],
    issues: list[IssueItem],
    regulations: list[dict],
) -> tuple[list[IssueItem], list[EvidenceItem]]:
    """Build evidence chain linking US 14117 issues to facts and regulations."""
    fact_ids = {fact.fact_id for fact in facts}
    default_rule_refs = [
        item.get("source_id", "")
        for item in regulations
        if item.get("source_id")
    ]
    if not default_rule_refs:
        default_rule_refs = [SECTION_COVERED_PERSON, SECTION_PROHIBITED_DEFINITION, SECTION_RESTRICTED_AUTHORIZATION]

    updated_issues: list[IssueItem] = []
    evidence_chain: list[EvidenceItem] = []

    for issue in issues:
        fact_refs = [ref for ref in issue.fact_refs if ref in fact_ids]
        if not fact_refs:
            # Fall back to any fact that seems related
            fact_refs = [f.fact_id for f in facts[:1]]

        evidence_id = _evidence_id(issue.issue_id)
        rule_refs = issue.rule_refs if issue.rule_refs else default_rule_refs[:3]

        confidence = 0.95 if issue.severity == "BLOCKER" else (
            0.90 if issue.severity == "HIGH" else (
                0.75 if issue.severity == "MEDIUM" else 0.60
            )
        )

        evidence_chain.append(
            EvidenceItem(
                evidence_id=evidence_id,
                claim=issue.title,
                fact_refs=fact_refs,
                rule_refs=rule_refs,
                conclusion=issue.recommended_action,
                confidence=confidence,
                used_by=[issue.issue_id, *issue.affects_outputs],
            )
        )
        updated_issues.append(issue.model_copy(update={"evidence_refs": [evidence_id]}))

    return updated_issues, evidence_chain
