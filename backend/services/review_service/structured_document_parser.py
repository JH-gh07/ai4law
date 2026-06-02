"""StructuredDocumentParser — parse documents into structured objects with
table, appendix field, and page-position awareness.

Extends beyond plain‑text extraction:
- Preserves page / paragraph position
- Detects and structures table content (field‑name → value mappings)
- Recognizes appendix fields (especially for SCC Annex I)
- Returns StructuredDocument with blocks and extracted fields
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader


# ── Appendix field patterns (SCC Annex I recognition) ───────────────────

_APPENDIX_FIELD_PATTERNS = [
    # Field label pattern → normalized field name
    (re.compile(r"[（(]?(处理目的|出境目的|使用目的)[）)]?[：:\s]*"), "处理目的"),
    (re.compile(r"[（(]?(处理方式|出境方式|传输方式|提供方式)[）)]?[：:\s]*"), "处理方式"),
    (re.compile(r"[（(]?(个人信息.*规模|出境.*规模|数据.*规模|涉及.*人数)[）)]?[：:\s]*"), "个人信息规模"),
    (re.compile(r"[（(]?(个人信息.*种类|数据类型|数据类别|信息种类|字段)[）)]?[：:\s]*"), "个人信息种类"),
    (re.compile(r"[（(]?(敏感个人信息.*种类|敏感.*数据.*种类)[）)]?[：:\s]*"), "敏感个人信息种类"),
    (re.compile(r"[（(]?(境外.*接收方|接收方.*名称|境外.*方|境外.*第三方)[）)]?[：:\s]*"), "境外接收方信息"),
    (re.compile(r"[（(]?(传输方式|传输途径|出境途径|网络传输|物理介质)[）)]?[：:\s]*"), "传输方式"),
    (re.compile(r"[（(]?(保存期限|存储期限|保留.*期限|保存.*期间)[）)]?[：:\s]*"), "保存期限"),
    (re.compile(r"[（(]?(保存地点|存储地点|存.*位置|服务器.*位置|数据中心|机房)[）)]?[：:\s]*"), "保存地点"),
    (re.compile(r"[（(]?(违约责任|赔偿责任|责任承担)[）)]?[：:\s]*"), "违约责任"),
    (re.compile(r"[（(]?(争议解决|管辖|法律适用)[）)]?[：:\s]*"), "争议解决"),
    (re.compile(r"[（(]?(再转移|转委托|子处理者|下级处理者)[）)]?[：:\s]*"), "再转移约束"),
    (re.compile(r"[（(]?(安全.*措施|技术.*措施|组织.*措施|保护.*措施)[）)]?[：:\s]*"), "安全措施"),
    (re.compile(r"[（(]?(数据.*范围|处理.*范围|数据.*内容)[）)]?[：:\s]*"), "数据范围"),
]


class DocumentBlock:
    """A structural block within a document page."""

    def __init__(
        self,
        block_type: str,  # "paragraph" | "table" | "heading" | "appendix_header"
        text: str = "",
        rows: list[list[str]] | None = None,
        position: int = 0,
    ) -> None:
        self.block_type = block_type
        self.text = text
        self.rows = rows or []
        self.position = position


class StructuredDocument:
    """Structured representation of a parsed document."""

    def __init__(
        self,
        file_id: str = "",
        filename: str = "",
        plain_text: str = "",
    ) -> None:
        self.file_id = file_id
        self.filename = filename
        self.plain_text = plain_text
        self.pages: list[dict[str, Any]] = []
        self.appendix_fields: dict[str, str] = {}
        self.tables: list[list[list[str]]] = []
        self.total_pages = 0


class StructuredDocumentParser:
    """Parse DOCX, PDF, and plain‑text files into StructuredDocument."""

    def parse(self, file_id: str, file_path: Path) -> StructuredDocument:
        """Parse a file and return a StructuredDocument."""
        ext = file_path.suffix.lower()
        filename = file_path.name

        if ext == ".docx":
            return self._parse_docx(file_id, filename, file_path)
        elif ext == ".pdf":
            return self._parse_pdf(file_id, filename, file_path)
        else:
            return self._parse_plain(file_id, filename, file_path)

    # ------------------------------------------------------------------
    # DOCX parsing — paragraph + table structure
    # ------------------------------------------------------------------

    def _parse_docx(self, file_id: str, filename: str, file_path: Path) -> StructuredDocument:
        doc = Document(str(file_path))
        doc_structure = StructuredDocument(file_id=file_id, filename=filename)
        blocks: list[DocumentBlock] = []
        page_num = 1
        all_text: list[str] = []
        pos = 0

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                para = None
                # Find the corresponding paragraph object
                for p in doc.paragraphs:
                    if p._element is element:
                        para = p
                        break
                if para and para.text.strip():
                    text = para.text.strip()
                    all_text.append(text)
                    pos += 1
                    style = para.style.name if para.style else ""
                    is_heading = "heading" in style.lower() or "Heading" in style
                    blocks.append(DocumentBlock(
                        block_type="heading" if is_heading else "paragraph",
                        text=text,
                        position=pos,
                    ))

            elif tag == "tbl":
                table_rows = []
                for table in doc.tables:
                    if table._element is element:
                        for row in table.rows:
                            cells = [cell.text.strip() for cell in row.cells]
                            table_rows.append(cells)
                        break
                if table_rows:
                    pos += 1
                    blocks.append(DocumentBlock(
                        block_type="table",
                        rows=table_rows,
                        position=pos,
                    ))
                    doc_structure.tables.append(table_rows)
                    # Also add as text for processing
                    table_text = "\n".join(" | ".join(r) for r in table_rows)
                    all_text.append(table_text)

        doc_structure.plain_text = "\n".join(all_text)
        doc_structure.pages = [{
            "page_no": page_num,
            "blocks": [
                {"type": b.block_type, "text": b.text, "rows": b.rows, "position": b.position}
                for b in blocks
            ],
        }]
        doc_structure.total_pages = 1
        doc_structure.appendix_fields = self._extract_appendix_fields(doc_structure.plain_text)
        return doc_structure

    # ------------------------------------------------------------------
    # PDF parsing — page‑aware
    # ------------------------------------------------------------------

    def _parse_pdf(self, file_id: str, filename: str, file_path: Path) -> StructuredDocument:
        reader = PdfReader(str(file_path))
        doc_structure = StructuredDocument(file_id=file_id, filename=filename)
        all_text: list[str] = []
        pages: list[dict[str, Any]] = []

        for page_idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            all_text.append(text)

            # Split into blocks (paragraphs)
            blocks: list[dict[str, Any]] = []
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                blocks.append({"type": "paragraph", "text": line})

            pages.append({
                "page_no": page_idx,
                "blocks": blocks,
            })

        doc_structure.plain_text = "\n".join(all_text)
        doc_structure.pages = pages
        doc_structure.total_pages = len(pages)
        doc_structure.appendix_fields = self._extract_appendix_fields(doc_structure.plain_text)
        return doc_structure

    # ------------------------------------------------------------------
    # Plain text parsing
    # ------------------------------------------------------------------

    def _parse_plain(self, file_id: str, filename: str, file_path: Path) -> StructuredDocument:
        text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        doc_structure = StructuredDocument(
            file_id=file_id, filename=filename, plain_text=text,
        )

        # Split into blocks (line by line)
        blocks: list[dict[str, Any]] = []
        for pos, line in enumerate(text.split("\n"), start=1):
            line = line.strip()
            if not line:
                continue
            # Detect Markdown tables
            if line.startswith("|") and line.endswith("|"):
                blocks.append({"type": "table", "text": line, "position": pos})
            else:
                blocks.append({"type": "paragraph", "text": line, "position": pos})

        doc_structure.pages = [{"page_no": 1, "blocks": blocks}]
        doc_structure.total_pages = 1
        doc_structure.appendix_fields = self._extract_appendix_fields(text)
        return doc_structure

    # ------------------------------------------------------------------
    # Appendix field extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_appendix_fields(text: str) -> dict[str, str]:
        """Extract appendix field‑name → value mappings from text."""
        fields: dict[str, str] = {}
        for pattern, field_name in _APPENDIX_FIELD_PATTERNS:
            m = pattern.search(text)
            if m:
                # Grab text after the match, until next newline or field marker
                start = m.end()
                segment = text[start:start + 300]
                # Stop at next field label or newline
                value = segment.split("\n")[0].strip()
                # Also stop at known field separators
                for sep in ["。", "；", "处理目的", "处理方式", "保存期限", "保存地点", "境外接收方"]:
                    idx = value.find(sep)
                    if idx > 0:
                        value = value[:idx].strip()
                if value and value not in fields.values():
                    fields[field_name] = value
        return fields

    # ------------------------------------------------------------------
    # Convenience: parse to plain text (backward compatible)
    # ------------------------------------------------------------------

    def parse_text_only(self, file_path: Path) -> str:
        """Extract only plain text (backward‑compatible shortcut)."""
        ext = file_path.suffix.lower()
        if ext == ".docx":
            doc = Document(str(file_path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif ext == ".pdf":
            reader = PdfReader(str(file_path))
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages
            ).strip()
        else:
            return file_path.read_text(encoding="utf-8", errors="ignore").strip()
