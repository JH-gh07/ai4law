"""Enhanced document parser wrapping FileParser with structure hints.

Extracts:
- Raw text (via existing FileParser)
- Page-level text for PDFs
- Structure hints from font size (PDF) or paragraph style (DOCX)
- Document-level metadata (title, date hints)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


@dataclass
class ParsedDocument:
    raw_text: str
    pages: list[str] = field(default_factory=list)
    structure_hints: list[dict] = field(default_factory=list)
    # extracted metadata
    title: str = ""
    publisher: str = ""
    publish_date: str = ""
    effective_date: str = ""


class DocumentParser:
    """Parse PDF and DOCX files into ParsedDocument with structure hints."""

    def parse_bytes(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf_bytes(file_bytes)
        if suffix == ".docx":
            return self._parse_docx_bytes(file_bytes)
        raise ValueError(f"Unsupported format: {suffix}")

    def parse_path(self, file_path: str) -> ParsedDocument:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(BytesIO(path.read_bytes()))
        if suffix == ".docx":
            return self._parse_docx(BytesIO(path.read_bytes()))
        raise ValueError(f"Unsupported format: {suffix}")

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_pdf_bytes(data: bytes) -> ParsedDocument:
        return DocumentParser._parse_pdf(BytesIO(data))

    @staticmethod
    def _parse_pdf(stream) -> ParsedDocument:
        reader = PdfReader(stream)
        pages: list[str] = []
        hints: list[dict] = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            stripped = page_text.strip()
            pages.append(stripped)
            if stripped:
                # Use first line of first page as title hint
                first_line = stripped.split("\n")[0].strip()
                if i == 0 and len(first_line) >= 4:
                    hints.append({"type": "potential_title", "text": first_line, "page": i + 1})

        title = ""
        if hints:
            title = hints[0]["text"][:200]

        return ParsedDocument(
            raw_text="\n".join(pages),
            pages=pages,
            structure_hints=hints,
            title=title,
        )

    # ------------------------------------------------------------------
    # DOCX
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_docx_bytes(data: bytes) -> ParsedDocument:
        return DocumentParser._parse_docx(BytesIO(data))

    @staticmethod
    def _parse_docx(stream) -> ParsedDocument:
        document = Document(stream)
        blocks: list[str] = []
        hints: list[dict] = []

        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            blocks.append(text)
            style_name = para.style.name if para.style else ""
            if style_name and "heading" in style_name.lower():
                hints.append({
                    "type": "heading",
                    "level": style_name,
                    "text": text,
                })

        raw_text = "\n".join(blocks)
        title = ""
        if hints:
            title = hints[0]["text"][:200]
        elif blocks:
            title = blocks[0][:200]

        return ParsedDocument(
            raw_text=raw_text,
            structure_hints=hints,
            title=title,
        )
