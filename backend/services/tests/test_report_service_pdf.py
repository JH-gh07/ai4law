from pathlib import Path

from pypdf import PdfReader

from backend.core.settings import Settings
from backend.services.report_service import ReportService


def test_report_service_pdf_renders_markdown_instead_of_literal_markers(
    tmp_path: Path,
) -> None:
    service = ReportService(Settings(report_dir=tmp_path))
    path = tmp_path / "report.pdf"

    service._write_pdf(path, ["## Risk heading", "- first item"])

    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    assert "Risk heading" in text
    assert "first item" in text
    assert "## Risk heading" not in text
