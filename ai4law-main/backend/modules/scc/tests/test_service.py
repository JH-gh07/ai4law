import zipfile
from pathlib import Path

from docx import Document

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
    assert "_SCC_" in result.report_path
    assert result.output_files["markdown"].endswith(".md")
    assert "_SCC_" in result.output_files["markdown"]
    assert len(result.chapters) == 4
    assert any("No SCC draft provided" in issue for issue in result.consistency_issues)


def test_scc_generate_annotated_docx(tmp_path: Path) -> None:
    source_docx = tmp_path / "sample.docx"
    document = Document()
    document.add_paragraph("个人信息出境标准合同")
    document.add_paragraph("甲方名称：测试公司")
    document.add_paragraph("乙方名称：Example Recipient Inc.")
    document.add_paragraph("双方应根据适用法律持续评估跨境传输风险。")
    document.save(source_docx)

    service = SCCService()
    payload = SCCRequest(
        company_name="测试公司",
        receiver_name="Example Recipient Inc.",
        receiver_country="Singapore",
        transfer_purpose="客户支持与系统运维",
        pii_count=200,
        spi_count=10,
        has_scc_draft=True,
        uploaded_files=[str(source_docx)],
    )

    result = service.generate_report(payload)

    assert "annotated_docx" in result.output_files
    annotated_path = Path(result.output_files["annotated_docx"])
    assert annotated_path.exists()

    with zipfile.ZipFile(annotated_path, "r") as archive:
        assert "word/comments.xml" in archive.namelist()
        document_xml = archive.read("word/document.xml").decode("utf-8")
        comments_xml = archive.read("word/comments.xml").decode("utf-8")

    assert "commentRangeStart" in document_xml
    assert "commentReference" in document_xml
    assert "风险点名称" in comments_xml
