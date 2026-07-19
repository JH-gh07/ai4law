from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import FactItem
from backend.domains.cn.security_assessment.schema import AssessmentRequest, CompanyProfile


def _fact_id(field_path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", field_path).strip("-")
    return f"FACT-{safe}"


def _diagnosis_value(diagnosis_result: object | None, field: str) -> Any:
    if diagnosis_result is None:
        return None
    if isinstance(diagnosis_result, dict):
        return diagnosis_result.get(field)
    return getattr(diagnosis_result, field, None)


def _schema_fact(field_path: str, value: Any, notes: str | None = None) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type="schema",
        source_ref="AssessmentRequest",
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=0.6,
        notes=notes,
        evidence_status="user_claim_only",
        can_support_external_positive_claim=False,
    )


def _diagnosis_fact(field_path: str, value: Any) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type="diagnosis",
        source_ref="DiagnosisResult",
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=1.0 if value is not None else 0.6,
        evidence_status="documented_evidence" if value is not None else "partial_evidence",
        can_support_external_positive_claim=value is not None,
    )


def build_assessment_facts(
    request: AssessmentRequest,
    profile: CompanyProfile,
    diagnosis_result: object | None = None,
) -> list[FactItem]:
    facts = [
        _schema_fact("request.company_name", request.company_name),
        _schema_fact("request.industry", request.industry),
        _schema_fact("request.is_ciio", request.is_ciio),
        _schema_fact("request.contains_important_data", request.contains_important_data),
        _schema_fact("request.pii_count", request.pii_count),
        _schema_fact("request.spi_count", request.spi_count),
        _schema_fact("request.transfer_purpose", request.transfer_purpose),
        _schema_fact("request.receiver_country", request.receiver_country),
        _schema_fact(
            "request.uploaded_files",
            list(request.uploaded_files),
            notes="Uploaded file paths are captured as a list, not as parsed content.",
        ),
        _schema_fact(
            "request.data_inventory_items",
            [item.model_dump() for item in request.data_inventory_items],
            notes="Structured data inventory items supplied by the user.",
        ),
        _schema_fact(
            "request.recipient_info",
            request.recipient_info.model_dump() if request.recipient_info else None,
        ),
        _schema_fact(
            "request.downstream_processors",
            [item.model_dump() for item in request.downstream_processors],
        ),
        _schema_fact(
            "request.legal_document_review",
            request.legal_document_review.model_dump() if request.legal_document_review else None,
        ),
        _schema_fact(
            "request.security_capability",
            request.security_capability.model_dump() if request.security_capability else None,
        ),
        _schema_fact(
            "request.compliance_history",
            request.compliance_history.model_dump() if request.compliance_history else None,
        ),
        _schema_fact(
            "request.personal_info_protection",
            request.personal_info_protection.model_dump() if request.personal_info_protection else None,
        ),
        _schema_fact(
            "request.system_link",
            request.system_link.model_dump() if request.system_link else None,
        ),
        _schema_fact(
            "request.self_assessment_info",
            request.self_assessment_info.model_dump() if request.self_assessment_info else None,
        ),
    ]

    for idx, note in enumerate(profile.extracted_notes, start=1):
        source_ref = note.split(":", 1)[0]
        facts.append(
            FactItem(
                fact_id=f"FACT-attachment-note-{idx}",
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

    facts.extend(
        [
            _diagnosis_fact(
                "diagnosis_result.recommended_path",
                _diagnosis_value(diagnosis_result, "recommended_path"),
            ),
            _diagnosis_fact("diagnosis_result.rationale", _diagnosis_value(diagnosis_result, "rationale")),
            _diagnosis_fact("diagnosis_result.risk_level", _diagnosis_value(diagnosis_result, "risk_level")),
            _diagnosis_fact(
                "diagnosis_result.matched_rule_id",
                _diagnosis_value(diagnosis_result, "matched_rule_id"),
            ),
        ]
    )
    return facts
