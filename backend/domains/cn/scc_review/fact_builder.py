"""CN SCC Fact Builder — extract structured FactItem objects from SCCRequest.

Produces facts that feed into the agent system, rule engine, and report generation.
Each fact tracks its source, confidence, evidence status, and whether it can
support positive external claims.

Reference: docs/archive/design-provenance/认证标准合同路径.md — Facts/Issues/Evidence layered architecture
"""

from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import FactItem
from backend.domains.cn.scc_review.schema import SCCProfile, SCCRequest


def _fact_id(field_path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", field_path).strip("-")
    return f"CN-SCC-FACT-{safe}"


def _schema_fact(
    field_path: str,
    value: Any,
    notes: str | None = None,
    confidence: float = 0.6,
    evidence_status: str = "user_claim_only",
) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type="schema",
        source_ref="SCCRequest",
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=confidence,
        notes=notes,
        evidence_status=evidence_status,
        can_support_external_positive_claim=False,
    )


def _derived_fact(
    field_path: str,
    value: Any,
    source_ref: str = "rule_engine",
    confidence: float = 0.8,
    evidence_status: str = "documented_evidence",
) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type="derived",
        source_ref=source_ref,
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=confidence,
        evidence_status=evidence_status,
        can_support_external_positive_claim=True,
    )


def build_scc_facts(request: SCCRequest, profile: SCCProfile) -> list[FactItem]:
    """Build structured facts from the SCC request and profile."""

    facts: list[FactItem] = [
        # ── Company identity ──
        _schema_fact("request.company_name", request.company_name),
        _schema_fact("request.industry", request.industry, confidence=0.6),
        _schema_fact("request.is_ciio", request.is_ciio,
                     notes="CIIO状态为用户自行声明" if request.is_ciio else None,
                     evidence_status="user_claim_only"),
        _schema_fact("request.has_important_data", request.has_important_data,
                     evidence_status="user_claim_only"),

        # ── Data transfer scope ──
        _schema_fact("request.transfer_purpose", request.transfer_purpose),
        _schema_fact("request.pii_count", request.pii_count,
                     notes=f"{request.pii_count:,}人"),
        _schema_fact("request.spi_count", request.spi_count,
                     notes=f"{request.spi_count:,}人"),
        _schema_fact("request.receiver_name", request.receiver_name),
        _schema_fact("request.receiver_country", request.receiver_country),
        _schema_fact("request.receiver_type", request.receiver_type.value,
                     evidence_status="user_claim_only"),

        # ── Legal basis ──
        _schema_fact("request.legal_basis",
                     [lb.value for lb in request.legal_basis],
                     notes="用户自行选择，未经系统核验",
                     evidence_status="user_claim_only"),

        # ── Path materials ──
        _schema_fact("request.has_scc_draft", request.has_scc_draft,
                     evidence_status="documented_evidence" if request.has_scc_draft else "user_claim_only"),
        _schema_fact("request.has_certification_material", request.has_certification_material,
                     evidence_status="documented_evidence" if request.has_certification_material else "user_claim_only"),
        _schema_fact("request.has_exemption_material", request.has_exemption_material,
                     evidence_status="documented_evidence" if request.has_exemption_material else "user_claim_only"),

        # ── HR management ──
        _schema_fact("request.is_hr_management", request.is_hr_management,
                     evidence_status="user_claim_only"),
        _schema_fact("request.is_certification_body", request.is_certification_body,
                     evidence_status="user_claim_only"),

        # ── User-provided evidence summaries ──
        _schema_fact("request.contract_summary_provided", bool(request.contract_summary),
                     evidence_status="documented_evidence" if request.contract_summary else "user_claim_only"),
        _schema_fact("request.privacy_policy_summary_provided", bool(request.privacy_policy_summary),
                     evidence_status="documented_evidence" if request.privacy_policy_summary else "user_claim_only"),
        _schema_fact("request.employee_handbook_summary_provided", bool(request.employee_handbook_summary),
                     evidence_status="documented_evidence" if request.employee_handbook_summary else "user_claim_only"),
        _schema_fact("request.consent_record_summary_provided", bool(request.consent_record_summary),
                     evidence_status="documented_evidence" if request.consent_record_summary else "user_claim_only"),

        # ── Files ──
        _schema_fact("request.uploaded_file_count", len(request.uploaded_files)),
        _schema_fact("request.data_field_count", len(request.data_fields)),
    ]

    # ── Derived facts from rule engine ──
    pii_count = request.pii_count
    if pii_count >= 1_000_000:
        facts.append(_derived_fact(
            "derived.pii_threshold_exceeded", True,
            source_ref="rule_engine:pii_threshold",
            confidence=1.0,
        ))
    if request.spi_count >= 10_000:
        facts.append(_derived_fact(
            "derived.spi_threshold_exceeded", True,
            source_ref="rule_engine:spi_threshold",
            confidence=1.0,
        ))
    if request.is_ciio:
        facts.append(_derived_fact(
            "derived.ciio_triggers_security_assessment", True,
            source_ref="rule_engine:ciio",
            confidence=1.0,
        ))
    if request.has_important_data:
        facts.append(_derived_fact(
            "derived.important_data_triggers_security_assessment", True,
            source_ref="rule_engine:important_data",
            confidence=1.0,
        ))

    # ── File attachment facts ──
    for note in profile.extracted_notes:
        facts.append(FactItem(
            fact_id=_fact_id(f"attachment.{note[:40]}"),
            source_type="attachment",
            source_ref=note.split(":", 1)[0] if ":" in note else "uploaded_file",
            field_path="attachment.parsed_text",
            value=note,
            confidence=0.7,
            evidence_status="documented_evidence",
            can_support_external_positive_claim=True,
        ))

    return facts
