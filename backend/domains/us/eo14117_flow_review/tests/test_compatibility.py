import pytest

from backend.domains.us.eo14117_flow_review.compatibility import (
    CompatibilityClarificationRequired,
    adapt_cn_flow_request,
)
from backend.domains.us.eo14117_flow_review.schema import CNFlowRequest


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
    assert result.canonical_request.onward_transfer is True
    assert result.canonical_request.attachments == ["data.csv", "entity.csv"]
    assert "attachments.content_unparsed" in result.lossy_fields
