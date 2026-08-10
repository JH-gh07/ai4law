"""US 14117 evidence builder — links issues to facts and regulations."""

from __future__ import annotations

import re

from backend.common.workflow import (
    CitationBinding,
    DocumentRef,
    EvidenceItem,
    FactItem,
    IssueItem,
    build_citation_bindings,
)
from backend.domains.us.eo14117.rule_engine import (
    SECTION_COVERED_PERSON,
    SECTION_PROHIBITED_DEFINITION,
    SECTION_RESTRICTED_AUTHORIZATION,
)


def _evidence_id(issue_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", issue_id).strip("-")
    return f"US14117-EVIDENCE-{safe}"


def _extract_document_refs(
    fact_refs: list[str],
    facts: list[FactItem],
) -> list[DocumentRef]:
    fact_map = {f.fact_id: f for f in facts}
    refs: list[DocumentRef] = []
    for fact_id in fact_refs:
        fact = fact_map.get(fact_id)
        if fact is None:
            continue
        material_refs = getattr(fact, "supporting_material_refs", None)
        if material_refs:
            for ref in material_refs:
                if isinstance(ref, dict):
                    refs.append(DocumentRef(**ref))
                elif isinstance(ref, DocumentRef):
                    refs.append(ref)
                elif hasattr(ref, "file_name"):
                    refs.append(DocumentRef(
                        file_name=getattr(ref, "file_name", ""),
                        page=getattr(ref, "page", 1),
                        quote=getattr(ref, "quote", ""),
                    ))
    return refs


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
                legal_basis=build_citation_bindings(regulations),
                document_refs=_extract_document_refs(fact_refs, facts),
                rag_query_used=f"us14117:{issue.issue_id}",
                rag_hits_count=len(regulations),
            )
        )
        updated_issues.append(issue.model_copy(update={"evidence_refs": [evidence_id]}))

    return updated_issues, evidence_chain
