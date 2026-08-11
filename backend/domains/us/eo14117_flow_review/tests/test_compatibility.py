import json
from pathlib import Path

import pytest

from backend.domains.us.eo14117_flow_review.compatibility import (
    CompatibilityClarificationRequired,
    adapt_cn_flow_request,
    project_us14117_request_to_cn_flow,
)
from backend.domains.us.eo14117_flow_review.schema import CNFlowRequest
from backend.domains.us.eo14117.rule_engine import run_rule_engine
from backend.domains.us.eo14117.schema import US14117Request

ROOT = Path(__file__).resolve().parents[5]


def _legacy_request() -> CNFlowRequest:
    return CNFlowRequest.model_validate(
        {
            "company_name": "示例企业",
            "transfer_purpose": "云服务监控",
            "data_categories": ["账户信息"],
            "sensitive_data_flags": [],
            "recipient_entities": [
                {"entity_name": "US ServiceCo", "country_region": "美国", "entity_role": "processor"}
            ],
            "transfer_chain": "CN Controller -> US ServiceCo",
            "attachments": [
                {"file_role": "data_inventory", "file_name": "data.csv", "file_format": "csv", "storage_uri": "data.csv"},
                {"file_role": "entity_inventory", "file_name": "entity.csv", "file_format": "csv", "storage_uri": "entity.csv"},
            ],
        }
    )


def test_legacy_request_requires_missing_result_critical_facts() -> None:
    with pytest.raises(CompatibilityClarificationRequired) as exc_info:
        adapt_cn_flow_request(_legacy_request())

    error = exc_info.value
    assert "data_items.us_person_count" in error.lossy_fields
    assert "transaction_type" in error.lossy_fields
    assert error.questions


def test_complete_legacy_request_converts_to_canonical_request() -> None:
    payload = _legacy_request().model_copy(
        update={
            "us_person_count": 100_000,
            "transaction_type": "vendor_agreement",
            "doj_data_category_by_item": {"账户信息": "covered_personal_identifiers"},
        }
    )

    result = adapt_cn_flow_request(payload)

    assert result.canonical_module == "us_14117"
    assert result.clarification_questions == []
    assert result.canonical_request.data_items[0].us_person_count == 100_000
    assert result.canonical_request.data_items[0].doj_data_category == "covered_personal_identifiers"
    assert result.canonical_request.recipient_entities[0].country_of_registration == "美国"
    assert result.canonical_request.onward_transfer is False
    assert result.canonical_request.attachments == ["data.csv", "entity.csv"]
    assert "onward_transfer" in result.lossy_fields
    assert "attachments.content_unparsed" in result.lossy_fields


def test_legacy_missing_facts_never_produce_canonical_request() -> None:
    with pytest.raises(CompatibilityClarificationRequired):
        adapt_cn_flow_request(_legacy_request())


def test_legacy_adapter_preserves_canonical_rule_result() -> None:
    payload = _legacy_request().model_copy(
        update={
            "us_person_count": 1_000,
            "transaction_type": "data_brokerage",
            "doj_data_category_by_item": {"账户信息": "biometric_identifiers"},
            "recipient_entities": [
                _legacy_request().recipient_entities[0].model_copy(
                    update={"country_region": "中国"}
                )
            ],
        }
    )
    adapted = adapt_cn_flow_request(payload).canonical_request
    direct = US14117Request.model_validate(adapted.model_dump())

    adapted_result = run_rule_engine(adapted)
    direct_result = run_rule_engine(direct)

    assert adapted_result.traffic_light.overall_light == direct_result.traffic_light.overall_light
    assert adapted_result.traffic_light.overall_light == "RED"
    assert {
        (item.rule_id, item.section_ref, item.hit) for item in adapted_result.all_rule_hits
    } == {
        (item.rule_id, item.section_ref, item.hit) for item in direct_result.all_rule_hits
    }


@pytest.mark.parametrize(
    ("scenario_dir", "expected_light"),
    [("geneguard_genomic_red", "RED"), ("geneguard_geolocation_yellow", "YELLOW")],
)
def test_shared_scenario_preserves_core_facts_and_light_through_legacy_adapter(
    scenario_dir: str, expected_light: str
) -> None:
    document = json.loads(
        (ROOT / "benchmarks" / "cases" / "us_14117" / scenario_dir / "scenario.json").read_text(encoding="utf-8")
    )
    direct = US14117Request.model_validate(document["request"])

    projected = project_us14117_request_to_cn_flow(direct)
    adapted = adapt_cn_flow_request(projected.legacy_request)

    assert adapted.canonical_request.company_name == direct.company_name
    assert adapted.canonical_request.transaction_type == direct.transaction_type
    assert adapted.canonical_request.data_items[0].data_item_name == direct.data_items[0].data_item_name
    assert adapted.canonical_request.data_items[0].us_person_count == direct.data_items[0].us_person_count
    assert adapted.canonical_request.data_items[0].doj_data_category == direct.data_items[0].doj_data_category
    assert adapted.canonical_request.recipient_entities[0].entity_name == direct.recipient_entities[0].entity_name
    assert run_rule_engine(direct).traffic_light.overall_light == expected_light
    assert run_rule_engine(adapted.canonical_request).traffic_light.overall_light == expected_light
    assert "access_persons" in projected.lossy_fields
    assert "security_measures" in projected.lossy_fields
