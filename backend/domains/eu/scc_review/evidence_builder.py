"""EU SCC evidence builder — links issues to facts and regulations."""

from __future__ import annotations

import re

from backend.common.workflow import EvidenceItem, FactItem, IssueItem


def _evidence_id(issue_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", issue_id).strip("-")
    return f"EU-SCC-EVIDENCE-{safe}"


def build_eu_scc_evidence(
    facts: list[FactItem], issues: list[IssueItem], regulations: list[dict],
) -> tuple[list[IssueItem], list[EvidenceItem]]:
    fact_ids = {f.fact_id for f in facts}
    default_rule_refs = [r.get("source_id", "") for r in regulations if r.get("source_id")]
    if not default_rule_refs:
        default_rule_refs = ["EU 2021/914", "GDPR Article 46", "Schrems II C-311/18"]

    updated: list[IssueItem] = []
    chain: list[EvidenceItem] = []

    for issue in issues:
        fact_refs = [ref for ref in issue.fact_refs if ref in fact_ids] or [f.fact_id for f in facts[:1]]
        eid = _evidence_id(issue.issue_id)
        rule_refs = issue.rule_refs or default_rule_refs[:3]
        conf = 0.95 if issue.severity == "BLOCKER" else (0.90 if issue.severity == "HIGH" else (0.75 if issue.severity == "MEDIUM" else 0.60))

        chain.append(EvidenceItem(
            evidence_id=eid, claim=issue.title, fact_refs=fact_refs,
            rule_refs=rule_refs, conclusion=issue.recommended_action,
            confidence=conf, used_by=[issue.issue_id, *issue.affects_outputs],
        ))
        updated.append(issue.model_copy(update={"evidence_refs": [eid]}))

    return updated, chain
