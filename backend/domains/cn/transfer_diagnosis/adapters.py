from __future__ import annotations

from backend.domains.cn.transfer_diagnosis.models import (
    DiagnosisFacts,
    FactSource,
    TriState,
)
from backend.modules.diagnosis.schema import DiagnosisAnswers

_MODULE_TO_CANONICAL_FIELDS = {
    "q1_is_ciio": "is_ciio",
    "q2_has_important_data": "contains_important_data",
    "q3_pii_count": "personal_info_count",
    "q4_spi_count": "sensitive_personal_info_count",
    "q5_no_personal_info": "no_personal_info",
    "q6_scenario": "transfer_scenario",
    "q7_receiver_type": "receiver_type",
    "q8_purpose": "transfer_purpose",
}


def facts_from_module(
    answers: DiagnosisAnswers,
    *,
    field_provenance: dict[str, FactSource] | None = None,
    missing_facts: list[str] | None = None,
) -> DiagnosisFacts:
    explicit_fields = answers.model_fields_set
    provenance = field_provenance or {
        canonical_name: (
            FactSource.USER
            if module_name in explicit_fields
            else FactSource.DEFAULT
        )
        for module_name, canonical_name in _MODULE_TO_CANONICAL_FIELDS.items()
    }
    return DiagnosisFacts(
        is_ciio=TriState(answers.q1_is_ciio.value),
        contains_important_data=TriState(
            answers.q2_has_important_data.value
        ),
        personal_info_count=answers.q3_pii_count,
        sensitive_personal_info_count=answers.q4_spi_count,
        no_personal_info=TriState(answers.q5_no_personal_info.value),
        transfer_scenario=answers.q6_scenario.value,
        receiver_type=answers.q7_receiver_type.value,
        transfer_purpose=answers.q8_purpose,
        field_provenance=provenance,
        missing_facts=missing_facts or [],
    )
