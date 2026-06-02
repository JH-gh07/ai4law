"""US 14117 fact builder — extracts structured facts from request + rule engine results."""

from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import FactItem
from backend.modules.us_14117.schema import (
    US14117Request,
    US14117RuleEngineResult,
)


def _fact_id(field_path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", field_path).strip("-")
    return f"US14117-FACT-{safe}"


def _fact(
    field_path: str,
    value: Any,
    *,
    source_type: str = "schema",
    source_ref: str | None = None,
    confidence: float = 1.0,
    evidence_status: str = "user_claim_only",
) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type=source_type,
        source_ref=source_ref or "US14117Request",
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=confidence,
        evidence_status=evidence_status,
    )


def build_us_14117_facts(
    payload: US14117Request,
    rule_engine_result: US14117RuleEngineResult,
) -> list[FactItem]:
    """Build structured facts from US14117Request and rule engine output."""
    facts: list[FactItem] = []

    # ── Request-level facts ──
    facts.append(_fact("request.project_name", payload.project_name))
    facts.append(_fact("request.transaction_description", payload.transaction_description))
    facts.append(_fact("request.transaction_type", payload.transaction_type))
    facts.append(_fact("request.company_name", payload.company_name))
    facts.append(_fact("request.onward_transfer", payload.onward_transfer))
    facts.append(_fact("request.onward_transfer_description", payload.onward_transfer_description))
    facts.append(_fact("request.attachments", list(payload.attachments)))
    facts.append(_fact("request.data_item_count", len(payload.data_items)))
    facts.append(_fact("request.recipient_entity_count", len(payload.recipient_entities)))
    facts.append(_fact("request.access_person_count", len(payload.access_persons)))
    facts.append(_fact("request.security_measure_count", len(payload.security_measures)))

    # ── Data item facts ──
    for item in payload.data_items:
        prefix = f"data_item.{item.data_item_name}"
        facts.append(_fact(f"{prefix}.us_person_count", item.us_person_count))
        facts.append(_fact(f"{prefix}.data_subject_type", item.data_subject_type))
        facts.append(_fact(f"{prefix}.doj_data_category", item.doj_data_category))
        facts.append(_fact(f"{prefix}.is_government_related", item.is_government_related))
        facts.append(_fact(f"{prefix}.is_sensitive_personal_info", item.is_sensitive_personal_info))

    # ── Entity facts ──
    for entity in payload.recipient_entities:
        prefix = f"entity.{entity.entity_name}"
        facts.append(_fact(f"{prefix}.country_of_registration", entity.country_of_registration))
        facts.append(_fact(f"{prefix}.governing_law", entity.governing_law))
        facts.append(_fact(f"{prefix}.government_control", entity.government_control))
        facts.append(_fact(f"{prefix}.entity_role", entity.entity_role))
        facts.append(_fact(f"{prefix}.is_covered_person", entity.is_covered_person))

    # ── Access person facts ──
    for person in payload.access_persons:
        prefix = f"access_person.{person.person_name}"
        facts.append(_fact(f"{prefix}.nationality", person.nationality))
        facts.append(_fact(f"{prefix}.country_of_residence", person.country_of_residence))
        facts.append(_fact(f"{prefix}.has_actual_access", person.has_actual_access))
        facts.append(_fact(f"{prefix}.access_type", person.access_type))

    # ── Rule engine derived facts ──
    # Data classifications
    for dc in rule_engine_result.data_classifications:
        prefix = f"classification.{dc['data_item_name']}"
        facts.append(_fact(
            f"{prefix}.doj_category", dc["doj_category"],
            source_type="derived", source_ref="RuleEngine",
        ))
        facts.append(_fact(
            f"{prefix}.bulk_threshold", dc["bulk_threshold"],
            source_type="derived", source_ref="RuleEngine",
        ))
        facts.append(_fact(
            f"{prefix}.threshold_hit", dc["threshold_hit"],
            source_type="derived", source_ref="RuleEngine",
        ))

    # Entity assessments
    for ea in rule_engine_result.entity_assessments:
        prefix = f"assessment.{ea['entity_name']}"
        facts.append(_fact(
            f"{prefix}.is_covered_person", ea["is_covered_person"],
            source_type="derived", source_ref="RuleEngine",
        ))
        facts.append(_fact(
            f"{prefix}.is_country_of_concern", ea["is_country_of_concern"],
            source_type="derived", source_ref="RuleEngine",
        ))

    # Transaction classification
    tc = rule_engine_result.transaction_classification
    facts.append(_fact("tx.is_prohibited", tc.get("is_prohibited", False), source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("tx.is_restricted", tc.get("is_restricted", False), source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("tx.involves_covered_person", tc.get("involves_covered_person", False), source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("tx.involves_bulk_sensitive", tc.get("involves_bulk_sensitive", False), source_type="derived", source_ref="RuleEngine"))

    # Traffic light
    tl = rule_engine_result.traffic_light
    facts.append(_fact("traffic_light.overall_light", tl.overall_light, source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("traffic_light.is_prohibited", tl.is_prohibited, source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("traffic_light.is_restricted", tl.is_restricted, source_type="derived", source_ref="RuleEngine"))

    return facts
