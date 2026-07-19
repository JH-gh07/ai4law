"""CN SCC Evidence Builder — link claims to facts and regulations, building EvidenceItem chains.

Each evidence item links a claim to:
- Supporting facts (fact_refs)
- Legal/regulation basis (rule_refs)
- A conclusion
- Confidence score
- Which chapters/reports use this evidence

Reference: docs/archive/design-provenance/认证标准合同路径.md — Facts/Issues/Evidence layered architecture
"""

from __future__ import annotations

from typing import Any

from backend.common.workflow import EvidenceItem, FactItem, IssueItem


def build_scc_evidence(
    facts: list[FactItem],
    issues: list[IssueItem],
    regulations: list[Any],
    path_diagnosis: Any | None = None,
) -> tuple[list[IssueItem], list[EvidenceItem]]:
    """Build evidence chains linking issues to facts and regulations.

    Each evidence item maps a claim to supporting facts, legal basis, and a conclusion.
    Returns updated issues (with evidence_refs populated) and evidence chain.
    """

    evidence_chain: list[EvidenceItem] = []
    counter = [0]

    def next_id() -> str:
        counter[0] += 1
        return f"CN-SCC-EVD-{counter[0]:03d}"

    regulation_refs = [getattr(r, "source_id", str(r)) for r in regulations]

    # Build fact lookup
    fact_by_field: dict[str, FactItem] = {}
    for f in facts:
        if f.field_path:
            fact_by_field[f.field_path] = f

    # ── Evidence for path determination ──
    pii_fact = fact_by_field.get("request.pii_count")
    spi_fact = fact_by_field.get("request.spi_count")
    ciio_fact = fact_by_field.get("request.is_ciio")
    important_fact = fact_by_field.get("request.has_important_data")

    if pii_fact and pii_fact.value:
        evidence_chain.append(EvidenceItem(
            evidence_id=next_id(),
            claim=f"出境个人信息规模为{pii_fact.value:,}人",
            fact_refs=[pii_fact.fact_id],
            rule_refs=regulation_refs[:2],
            conclusion=f"个人信息规模为{pii_fact.value:,}人，{'达到' if pii_fact.value >= 1000000 else '未达到'}安全评估门槛",
            confidence=0.9,
            used_by=["path_diagnosis", "PIPIA报告"],
        ))

    if spi_fact and spi_fact.value:
        evidence_chain.append(EvidenceItem(
            evidence_id=next_id(),
            claim=f"出境敏感个人信息规模为{spi_fact.value:,}人",
            fact_refs=[spi_fact.fact_id],
            rule_refs=regulation_refs[:2],
            conclusion=f"敏感个人信息规模为{spi_fact.value:,}人，{'达到' if spi_fact.value >= 10000 else '未达到'}安全评估门槛",
            confidence=0.9,
            used_by=["path_diagnosis", "PIPIA报告"],
        ))

    if ciio_fact and ciio_fact.value is True:
        evidence_chain.append(EvidenceItem(
            evidence_id=next_id(),
            claim="企业为关键信息基础设施运营者(CIIO)",
            fact_refs=[ciio_fact.fact_id],
            rule_refs=regulation_refs[:2],
            conclusion="CIIO身份触发安全评估义务，个人信息出境须通过安全评估",
            confidence=0.6 if ciio_fact.evidence_status == "user_claim_only" else 0.9,
            used_by=["path_diagnosis", "PIPIA报告"],
        ))

    if important_fact and important_fact.value is True:
        evidence_chain.append(EvidenceItem(
            evidence_id=next_id(),
            claim="涉及重要数据出境",
            fact_refs=[important_fact.fact_id],
            rule_refs=regulation_refs[:2],
            conclusion="重要数据出境须通过安全评估",
            confidence=0.6 if important_fact.evidence_status == "user_claim_only" else 0.9,
            used_by=["path_diagnosis", "PIPIA报告"],
        ))

    # ── Evidence for legal basis ──
    legal_basis_fact = fact_by_field.get("request.legal_basis")
    if legal_basis_fact and legal_basis_fact.value:
        evidence_chain.append(EvidenceItem(
            evidence_id=next_id(),
            claim=f"用户选择合法性基础：{legal_basis_fact.value}",
            fact_refs=[legal_basis_fact.fact_id],
            rule_refs=regulation_refs[:2],
            conclusion=f"合法性基础为用户自行选择，需进一步核验证据支撑",
            confidence=0.5,
            used_by=["legal_basis_review", "PIPIA报告"],
        ))

    # ── Evidence for contract existence ──
    scc_fact = fact_by_field.get("request.has_scc_draft")
    if scc_fact is not None:
        evidence_chain.append(EvidenceItem(
            evidence_id=next_id(),
            claim="标准合同草案存在性",
            fact_refs=[scc_fact.fact_id],
            rule_refs=regulation_refs[:1],
            conclusion=f"标准合同草案{'已提供' if scc_fact.value else '未提供'}",
            confidence=0.8 if scc_fact.value else 1.0,
            used_by=["contract_review", "PIPIA报告"],
        ))

    # ── Evidence for HR exemption ──
    hr_fact = fact_by_field.get("request.is_hr_management")
    handbook_fact = fact_by_field.get("request.employee_handbook_summary_provided")
    if hr_fact and hr_fact.value is True:
        evidence_chain.append(EvidenceItem(
            evidence_id=next_id(),
            claim="用户主张人力资源管理豁免",
            fact_refs=[hr_fact.fact_id] + ([handbook_fact.fact_id] if handbook_fact else []),
            rule_refs=regulation_refs[:2],
            conclusion=f"人力资源管理豁免{'有部分证据' if (handbook_fact and handbook_fact.value) else '证据不足'}支撑",
            confidence=0.6 if (handbook_fact and handbook_fact.value) else 0.3,
            used_by=["path_diagnosis", "PIPIA报告"],
        ))

    # ── Populate evidence_refs on issues ──
    for issue in issues:
        # Link evidence items that share fact refs with the issue
        matching_evidence = [
            ev.evidence_id for ev in evidence_chain
            if set(ev.fact_refs) & set(issue.fact_refs)
        ]
        if matching_evidence:
            issue.evidence_refs = list(set(issue.evidence_refs + matching_evidence))

    return issues, evidence_chain
