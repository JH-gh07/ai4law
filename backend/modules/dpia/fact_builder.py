"""DPIA fact builder — converts DPIARequest fields + need assessment into FactItems."""

from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import FactItem
from backend.modules.dpia.schema import DPIAProjectProfile, DPIARequest


def _fact_id(field_path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", field_path).strip("-")
    return f"DPIA-FACT-{safe}"


def _schema_fact(field_path: str, value: Any) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type="schema",
        source_ref="DPIARequest",
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=0.6,
        evidence_status="user_claim_only",
        can_support_external_positive_claim=False,
    )


def _diagnosis_fact(field_path: str, value: Any) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type="diagnosis",
        source_ref="DPIANeedAssessment",
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=1.0 if value is not None else 0.6,
        evidence_status="documented_evidence" if value is not None else "partial_evidence",
        can_support_external_positive_claim=value is not None,
    )


def build_dpia_facts(
    request: DPIARequest,
    profile: DPIAProjectProfile,
    diagnosis_result: object | None = None,
) -> list[FactItem]:
    """Build structured facts from DPIA request, profile, and need assessment."""

    # ── Schema facts from request ──
    facts: list[FactItem] = [
        _schema_fact("dpia.project_name", request.project_name),
        _schema_fact("dpia.project_goal", request.project_goal),
        _schema_fact("dpia.processing_flow_description", request.processing_flow_description),
        _schema_fact("dpia.data_categories", request.data_categories),
        _schema_fact("dpia.special_category_data", request.special_category_data),
        _schema_fact("dpia.special_category_types", request.special_category_types),
        _schema_fact("dpia.data_subject_categories", request.data_subject_categories),
        _schema_fact("dpia.data_subject_count", request.data_subject_count),
        _schema_fact("dpia.retention_period", request.retention_period),
        _schema_fact("dpia.cross_border_transfer", request.cross_border_transfer),
        _schema_fact("dpia.transfer_destination", request.transfer_destination),
        _schema_fact("dpia.automated_decision_making", request.automated_decision_making),
        _schema_fact("dpia.systematic_monitoring", request.systematic_monitoring),
        _schema_fact("dpia.large_scale_processing", request.large_scale_processing),
        _schema_fact("dpia.data_matching", request.data_matching),
        _schema_fact("dpia.new_technology", request.new_technology),
        _schema_fact("dpia.vulnerable_data_subjects", request.vulnerable_data_subjects),
        _schema_fact("dpia.consulted_internal_departments", request.consulted_internal_departments),
        _schema_fact("dpia.external_experts", request.external_experts),
        _schema_fact("dpia.data_subject_consultation_plan", request.data_subject_consultation_plan),
        _schema_fact("dpia.lawful_basis", request.lawful_basis),
        _schema_fact("dpia.necessity_statement", request.necessity_statement),
        _schema_fact("dpia.proportionality_statement", request.proportionality_statement),
        _schema_fact("dpia.transparency_information", request.transparency_information),
        _schema_fact("dpia.dpia_owner", request.dpia_owner),
        _schema_fact("dpia.dpo_name", request.dpo_name),
        _schema_fact("dpia.dpo_opinion", request.dpo_opinion),
        _schema_fact("dpia.review_date", request.review_date),
        _schema_fact("dpia.identified_risks_count", len(request.identified_risks)),
        _schema_fact("dpia.mitigation_measures_count", len(request.mitigation_measures)),
        _schema_fact(
            "dpia.uploaded_files",
            list(request.uploaded_files),
        ),
    ]

    # ── Attachment notes from profile ──
    for idx, note in enumerate(profile.extracted_notes, start=1):
        source_ref = note.split(":", 1)[0]
        facts.append(
            FactItem(
                fact_id=f"DPIA-FACT-attachment-note-{idx}",
                source_type="attachment",
                source_ref=source_ref,
                field_path=f"profile.extracted_notes[{idx - 1}]",
                value=note,
                normalized_value=note,
                confidence=0.8,
                evidence_status="partial_evidence",
                supporting_material_refs=[source_ref],
                can_support_external_positive_claim=False,
            )
        )

    # ── Diagnosis facts from need assessment ──
    if diagnosis_result is not None:
        dpia_required = _diagnosis_value(diagnosis_result, "dpia_required")
        prior_consult = _diagnosis_value(diagnosis_result, "prior_consultation_possible")
        reasoning = _diagnosis_value(diagnosis_result, "reasoning")
        triggers = _diagnosis_value(diagnosis_result, "trigger_reasons")

        facts.extend([
            _diagnosis_fact("dpia_need.dpia_required", dpia_required),
            _diagnosis_fact("dpia_need.prior_consultation_possible", prior_consult),
            _diagnosis_fact("dpia_need.reasoning", reasoning),
            _diagnosis_fact("dpia_need.trigger_reasons", triggers),
        ])

    # ── Risk input facts ──
    for risk in request.identified_risks:
        facts.append(
            _schema_fact(
                f"dpia.identified_risks.{risk.risk_id}",
                f"{risk.risk_description} (likelihood={risk.likelihood}, impact={risk.impact})",
            )
        )

    # ── Mitigation input facts ──
    for mitigation in request.mitigation_measures:
        facts.append(
            _schema_fact(
                f"dpia.mitigation_measures.{mitigation.mitigation_id}",
                f"{mitigation.description} (status={mitigation.status})",
            )
        )

    return facts


def _diagnosis_value(diagnosis_result: object | None, field: str) -> Any:
    if diagnosis_result is None:
        return None
    if isinstance(diagnosis_result, dict):
        return diagnosis_result.get(field)
    return getattr(diagnosis_result, field, None)
