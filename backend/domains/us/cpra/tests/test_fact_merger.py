from backend.domains.us.cpra.fact_merger import CPRAFactMerger
from backend.domains.us.cpra.schema import (
    CPRAAttachment,
    CPRADataItem,
    CPRADSRMechanism,
    CPRAFactPack,
    CPRARequest,
    CPRAVendorInfo,
)


def _build_request() -> CPRARequest:
    return CPRARequest.model_validate(
        {
            "company_name": "测试企业",
            "business_model": "SaaS",
            "data_lifecycle": "收集-处理-存储-删除",
            "notice_and_consent": "notice text",
            "consumer_rights_process": "rights text",
            "opt_out_and_sale_sharing": "opt out text",
            "vendor_management": "",
            "attachments": [
                {
                    "file_role": "privacy_policy",
                    "file_name": "policy.url",
                    "file_format": "url",
                    "storage_uri": "https://example.com/privacy",
                }
            ],
        }
    )


def test_fact_merger_backfills_missing_structured_fields() -> None:
    merger = CPRAFactMerger()
    payload = _build_request()

    merged = merger.merge(
        payload,
        [
            CPRAFactPack(
                source_file=CPRAAttachment(
                    file_role="data_map",
                    file_name="map.csv",
                    file_format="csv",
                    storage_uri="storage/uploads/map.csv",
                ),
                extracted_data_items=[
                    CPRADataItem(category="health_data", is_sensitive=True, purpose="analytics"),
                ],
                extracted_dsr_mechanism=CPRADSRMechanism(
                    has_web_form=True,
                    has_email=True,
                    response_days=30,
                    supports_access=True,
                ),
                extracted_vendors=[
                    CPRAVendorInfo(name="Vendor A", has_dpa=True, dpa_requires_dsr_assist=True),
                ],
            )
        ],
    )

    assert len(merged.data_items) == 1
    assert merged.data_items[0].category == "health_data"
    assert merged.dsr_mechanism is not None
    assert merged.dsr_mechanism.response_days == 30
    assert len(merged.vendors) == 1
    assert merged.vendors[0].name == "Vendor A"


def test_fact_merger_preserves_explicit_user_input() -> None:
    merger = CPRAFactMerger()
    payload = _build_request().model_copy(
        update={
            "data_items": [CPRADataItem(category="user_item", is_sensitive=False)],
            "dsr_mechanism": CPRADSRMechanism(has_email=True, response_days=45),
            "vendors": [CPRAVendorInfo(name="User Vendor", has_dpa=False)],
        }
    )

    merged = merger.merge(
        payload,
        [
            CPRAFactPack(
                source_file=CPRAAttachment(
                    file_role="vendor_list",
                    file_name="vendors.csv",
                    file_format="csv",
                    storage_uri="storage/uploads/vendors.csv",
                ),
                extracted_data_items=[CPRADataItem(category="agent_item", is_sensitive=True)],
                extracted_dsr_mechanism=CPRADSRMechanism(has_web_form=True, response_days=30),
                extracted_vendors=[CPRAVendorInfo(name="Agent Vendor", has_dpa=True)],
            )
        ],
    )

    assert [item.category for item in merged.data_items] == ["user_item"]
    assert merged.dsr_mechanism is not None
    assert merged.dsr_mechanism.response_days == 45
    assert [vendor.name for vendor in merged.vendors] == ["User Vendor"]
