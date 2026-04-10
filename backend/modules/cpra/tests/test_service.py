from backend.modules.cpra.schema import CPRARequest
from backend.modules.cpra.service import CPRAService


def test_cpra_generate_report() -> None:
    service = CPRAService()
    payload = CPRARequest.model_validate(
        {
            "company_name": "测试企业",
            "business_model": "SaaS",
            "data_lifecycle": "收集-处理-存储-删除",
            "notice_and_consent": "隐私告知缺失",
            "consumer_rights_process": "目前仅邮箱接收",
            "opt_out_and_sale_sharing": "存在共享但无opt-out",
            "vendor_management": "供应商管理未体现DPA",
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

    result = service.generate_report(payload)
    assert result.report_path.endswith(".docx")
    assert "_CPRA_合规全景报告_草案_" in result.report_path
    assert result.output_files["pdf"].endswith(".pdf")
    assert result.output_files["xlsx"].endswith(".xlsx")
    assert result.gap_items
