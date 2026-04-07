from backend.modules.tia.schema import TIARequest
from backend.modules.tia.service import TIAService


def test_tia_generate_report() -> None:
    service = TIAService()
    payload = TIARequest.model_validate(
        {
            "transfer_tool": "scc",
            "data_exporter_profile": "EU Exporter A",
            "data_importer_profile": "US Importer B",
            "third_country_assessment": "存在政府访问风险",
            "supplementary_measures": "端到端加密、严格密钥管理、访问透明报告",
            "final_conclusion": "在补充措施生效前提下SCC可传输",
            "attachments": [
                {
                    "file_role": "transfer_agreement",
                    "file_name": "agreement.pdf",
                    "file_format": "pdf",
                    "storage_uri": "storage://uploads/agreement.pdf",
                }
            ],
        }
    )

    result = service.generate_report(payload)

    assert result.report_path.endswith("_tia_report.docx")
    assert result.output_files["zip"].endswith("_tia_output_bundle.zip")
    assert len(result.chapters) == 6
    assert result.transfer_tool == "scc"

