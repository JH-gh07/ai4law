from pathlib import Path

from docx import Document
from pypdf import PdfWriter

from backend.common.storage.file_parser import FileParser


def test_parse_docx(tmp_path: Path) -> None:
    path = tmp_path / "sample.docx"
    doc = Document()
    doc.add_paragraph("hello compliance")
    doc.save(str(path))

    parser = FileParser()
    text = parser.parse_text(str(path))

    assert "hello compliance" in text


def test_parse_pdf(tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as fp:
        writer.write(fp)

    parser = FileParser()
    text = parser.parse_text(str(path))

    assert isinstance(text, str)
