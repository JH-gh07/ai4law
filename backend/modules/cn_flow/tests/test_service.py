from backend.modules.cn_flow.schema import CNFlowRequest
from backend.modules.cn_flow.service import CNFlowService


def test_cn_flow_generate_report() -> None:
    service = CNFlowService()
    payload = CNFlowRequest.model_validate(
        {
            "company_name": "测试企业",
            "transfer_purpose": "全球客服与风控",
            "data_categories": ["账户信息", "设备信息"],
            "sensitive_data_flags": ["生物识别"],
            "recipient_entities": [
                {
                    "entity_name": "US ServiceCo",
                    "country_region": "United States",
                    "entity_role": "processor",
                    "is_restricted_party": False,
                }
            ],
            "transfer_chain": "CN -> US processor -> subprocessor",
            "attachments": [
                {
                    "file_role": "data_inventory",
                    "file_name": "data.csv",
                    "file_format": "csv",
                    "storage_uri": "storage://uploads/data.csv",
                },
                {
                    "file_role": "entity_inventory",
                    "file_name": "entity.csv",
                    "file_format": "csv",
                    "storage_uri": "storage://uploads/entity.csv",
                },
            ],
        }
    )

    result = service.generate_report(payload)
    assert result.report_path.endswith(".docx")
    assert "_14117_风险评估结论报告_草案_" in result.report_path
    assert result.output_files["pdf"].endswith(".pdf")
    assert result.output_files["xlsx"].endswith(".xlsx")
    assert result.output_files["zip"].endswith(".zip")
    assert result.risk_items
