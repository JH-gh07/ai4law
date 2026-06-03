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


def test_cpra_generate_report_uses_enhanced_attachment_facts() -> None:
    service = CPRAService()
    payload = CPRARequest.model_validate(
        {
            "company_name": "测试企业",
            "business_model": "Health app",
            "data_lifecycle": "收集-处理-共享",
            "notice_and_consent": "notice text",
            "consumer_rights_process": "rights text",
            "opt_out_and_sale_sharing": "share text",
            "vendor_management": "",
            "attachments": [
                {
                    "file_role": "data_map",
                    "file_name": "map.csv",
                    "file_format": "csv",
                    "storage_uri": "storage/uploads/map.csv",
                }
            ],
        }
    )

    service.extractor.extract = lambda _attachment: {
        "role": "data_map",
        "categories": ["health_data"],
        "spi_categories": ["health_data"],
        "has_purposes": True,
        "has_recipients": True,
        "has_retention": True,
    }
    captured = {}

    def _fake_render(payload, chapters, gaps, attachment_notes):
        captured["payload"] = payload
        captured["gaps"] = gaps
        return {
            "markdown": "outputs/cpra/test.md",
            "docx": "outputs/cpra/test.docx",
            "pdf": "outputs/cpra/test.pdf",
            "xlsx": "outputs/cpra/test.xlsx",
            "zip": "outputs/cpra/test.zip",
        }

    service._render = _fake_render

    result = service.generate_report(payload)

    assert captured["payload"].data_items
    assert captured["payload"].data_items[0].category == "health_data"
    assert any(g.domain == "spi" for g in captured["gaps"])
    assert result.output_files["docx"].endswith(".docx")
