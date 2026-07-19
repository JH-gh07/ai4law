from backend.domains.eu.tia.schema import TIARequest
from backend.domains.eu.tia.service import TIAService


def _fast_render(task_id, payload, chapters, attachment_notes, citation_registry):
    return {
        "markdown": "outputs/tia/test.md",
        "docx": "outputs/tia/test.docx",
        "zip": "outputs/tia/test.zip",
        "citation_map_json": "outputs/tia/citation_map.json",
    }


def test_tia_generate_report() -> None:
    service = TIAService()
    service._render = _fast_render
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

    assert result.report_path.endswith(".docx")
    assert result.report_path == "outputs/tia/test.docx"
    assert result.output_files["zip"].endswith(".zip")
    assert result.output_files["zip"] == "outputs/tia/test.zip"
    assert result.output_files["citation_map_json"] == "outputs/tia/citation_map.json"
    assert len(result.chapters) == 6
    assert result.transfer_tool == "scc"


def test_tia_citation_bundle_produces_structured_citations() -> None:
    service = TIAService()
    payload = TIARequest.model_validate(
        {
            "transfer_tool": "scc",
            "data_exporter_profile": "EU Exporter A",
            "data_importer_profile": "US Importer B",
            "third_country_assessment": "US surveillance law may create government access risk.",
            "supplementary_measures": "Encryption, EU key separation, transparency reporting.",
            "final_conclusion": "SCC transfer requires supplementary measures under GDPR Article 46.",
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

    class _Reg:
        id = "eu_gdpr_art46"
        title = "GDPR"
        article = "Article 46"
        content = "A controller or processor may transfer personal data to a third country only if appropriate safeguards are provided."

    bundle = service._build_tia_citation_bundle(
        payload=payload,
        regs=[_Reg()],
        level="HIGH",
        route=None,
        country_risk_result=None,
        measure_overall="conditional",
    )

    assert bundle.items
    assert bundle.items[0].citation_id.startswith("CIT-EU-GDPR-ART46-")
    assert bundle.items[0].display_label == "GDPR Article 46"
    assert "{{CIT-EU-GDPR-ART46-" in bundle.prompt_block
