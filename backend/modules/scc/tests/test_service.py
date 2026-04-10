from backend.modules.scc.schema import SCCRequest
from backend.modules.scc.service import SCCService


def test_scc_generate_report() -> None:
    service = SCCService()
    payload = SCCRequest(
        company_name="测试公司",
        receiver_name="Test SG",
        receiver_country="Singapore",
        transfer_purpose="跨境客服",
        pii_count=120000,
        spi_count=500,
        has_scc_draft=False,
        uploaded_files=[],
    )

    result = service.generate_report(payload)

    assert result.report_path.endswith(".docx")
    assert "_SCC_合规审查报告_草案_" in result.report_path
    assert result.output_files["markdown"].endswith(".md")
    assert "_SCC_合规审查报告_草案_" in result.output_files["markdown"]
    assert len(result.chapters) == 4
    assert any("No SCC draft provided" in issue for issue in result.consistency_issues)
