"""EU SCC fact builder — extracts structured facts from review request + rule engine results."""

from __future__ import annotations

import re

from backend.common.workflow import FactItem
from backend.modules.eu_scc.schema import SCCReviewRequest, SCCRuleEngineResult


def _fact_id(field_path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", field_path).strip("-")
    return f"EU-SCC-FACT-{safe}"


def _fact(field_path: str, value, *, source_type="schema", source_ref="SCCReviewRequest", confidence=1.0) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path), source_type=source_type, source_ref=source_ref,
        field_path=field_path, value=value, normalized_value=value, confidence=confidence,
        evidence_status="user_claim_only",
    )


def build_eu_scc_facts(request: SCCReviewRequest, rule_result: SCCRuleEngineResult) -> list[FactItem]:
    facts: list[FactItem] = []

    # Request facts
    facts.append(_fact("request.project_name", request.project_name))
    facts.append(_fact("request.declared_module_type", request.declared_module_type))
    facts.append(_fact("request.exporter_role", request.exporter_role))
    facts.append(_fact("request.importer_role", request.importer_role))
    facts.append(_fact("request.has_tia", request.has_tia))
    facts.append(_fact("request.has_supplementary_measures", request.has_supplementary_measures))

    # Document facts
    doc = rule_result.document
    facts.append(_fact("doc.module_type", doc.module_type))
    facts.append(_fact("doc.clause_count", len(doc.clauses)))
    facts.append(_fact("doc.annex_ia.party_count", len(doc.annex_i_a.parties)))
    facts.append(_fact("doc.annex_ii.tom_count", len(doc.annex_ii.tom_items)))
    facts.append(_fact("doc.annex_iii.sub_processor_count", len(doc.annex_iii.sub_processors)))

    # Transfer chain
    chain = rule_result.transfer_chain
    facts.append(_fact("chain.exporter_role", chain.exporter_role))
    facts.append(_fact("chain.importer_role", chain.importer_role))
    facts.append(_fact("chain.sub_processor_count", len(chain.sub_processors)))

    # Rule engine results
    mv = rule_result.module_validation
    facts.append(_fact("review.module_is_correct", mv.is_correct, source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("review.expected_module", mv.expected_module, source_type="derived", source_ref="RuleEngine"))

    cc = rule_result.clause_comparison
    facts.append(_fact("review.clauses_checked", cc.clauses_checked, source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("review.deviations_found", cc.deviations_found, source_type="derived", source_ref="RuleEngine"))

    tia = rule_result.tia_review
    facts.append(_fact("review.has_third_country_transfer", tia.has_third_country_transfer, source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("review.tia_present", tia.tia_present, source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("review.schrems_ii_measures", tia.schrems_ii_measures_present, source_type="derived", source_ref="RuleEngine"))

    facts.append(_fact("review.overall_rating", rule_result.overall_rating, source_type="derived", source_ref="RuleEngine"))
    facts.append(_fact("review.finding_count", len(rule_result.all_findings), source_type="derived", source_ref="RuleEngine"))

    return facts
