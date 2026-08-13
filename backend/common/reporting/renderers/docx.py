"""IR → DOCX native renderer (task067 T05).

Produces an editable, structurally inspectable Word report directly from a v4
``DocumentIR`` — never from legacy chapter/template strings. The output uses
native Word structures only:

- A4 + unified margins from the resolved render profile;
- ``Heading 1..6`` for sections (Word outline levels) and ``keepNext`` so a
  heading/finding title never detaches from its first paragraph;
- native tables for the report metadata and the finding summary (short columns,
  repeated header row), never the legacy six-column detail table;
- finding detail rendered as vertical field blocks (statement / legal basis /
  recommendation / suggested revision);
- ``ClauseNode`` trees mapped to a real ``word/numbering.xml`` multi-level
  definition (``w:numPr``) rather than hand-written ``1.``/``(a)`` text;
- a header and a footer with a live ``PAGE`` field;
- a unified citation-note style for the citation appendix.

Markdown syntax (``**``/``__``/``| --- |``) is never written into paragraphs.
Unknown block types and unknown render profiles raise :class:`DocxRenderError`
(fail-closed).
"""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Mm, Pt
from docx.table import _Row
from docx.text.paragraph import Paragraph

from backend.common.reporting.render_profiles import RenderProfile, get_profile
from backend.common.reporting.schema import (
    Block,
    CitationNoteBlock,
    ClauseGroupBlock,
    ClauseNode,
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    FindingReferenceBlock,
    FindingSummaryBlock,
    ListItem,
    SectionIR,
)
from backend.common.reporting.schema.citations import CitationRecord, CitationRegistry


class DocxRenderError(RuntimeError):
    """Raised when a DocumentIR cannot be rendered to DOCX."""


_FIELD_LABELS = {
    "statement": "现状",
    "legal_basis": "法规依据",
    "recommendation": "整改建议",
    "suggested_revision": "建议修改文本",
}

_SUMMARY_LABELS = {
    "finding_id": "编号",
    "risk_level": "风险等级",
    "title": "标题",
    "status": "状态",
}

_WARNING_LABELS = {"info": "提示", "warning": "警告", "error": "错误", "fatal": "严重"}

_MAX_CLAUSE_DEPTH = 4

_NUMFMT_BY_STYLE = {
    "decimal": "decimal",
    "lower_alpha": "lowerLetter",
    "lower_roman": "lowerRoman",
}


# ── numbering helpers ───────────────────────────────────────────────────────

def _to_roman(value: int) -> str:
    result = ""
    remainder = value
    for numeral, symbol in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
                            (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
                            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while remainder >= numeral:
            result += symbol
            remainder -= numeral
    return result


class DocxRenderer:
    """Render a v4 ``DocumentIR`` into a native Word document."""

    def render(self, document: DocumentIR, registry: CitationRegistry | None = None) -> bytes:
        registry = registry or CitationRegistry(document.citations)
        profile = get_profile(document.render_contract.profile_id)
        findings = {finding.finding_id: finding for finding in document.findings}
        self._assign_citation_numbers(document, registry)

        doc = Document()
        self._configure_page(doc, profile)
        self._ensure_styles(doc, profile)
        self._add_header_footer(doc, document, profile)

        self._render_metadata(doc, document, profile)
        for section in document.sections:
            self._render_section(doc, section, findings, registry, profile)

        buffer = BytesIO()
        doc.save(buffer)
        return _normalize_zip_timestamps(buffer.getvalue())

    def render_to_file(
        self,
        document: DocumentIR,
        output_path: Path,
        registry: CitationRegistry | None = None,
    ) -> Path:
        """Render to a file path (creates parent directories) and return it."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.render(document, registry))
        return output_path

    # ── citation numbering (first-use order, mirroring the compiler) ──────

    @staticmethod
    def _iter_clause_nodes(clauses: list[ClauseNode]) -> Iterator[ClauseNode]:
        for clause in clauses:
            yield clause
            yield from DocxRenderer._iter_clause_nodes(clause.children)

    @staticmethod
    def _iter_citation_refs(document: DocumentIR) -> Iterator[str]:
        for section in document.sections:
            for block in section.blocks:
                for citation_id in getattr(block, "citation_refs", []):
                    yield citation_id
                for clause in DocxRenderer._iter_clause_nodes(getattr(block, "clauses", [])):
                    for citation_id in clause.citation_refs:
                        yield citation_id
        for finding in document.findings:
            for citation_id in finding.citation_refs:
                yield citation_id

    @staticmethod
    def _assign_citation_numbers(document: DocumentIR, registry: CitationRegistry) -> None:
        for citation_id in DocxRenderer._iter_citation_refs(document):
            if registry.resolve(citation_id) is not None:
                registry.assign_footnote_number(citation_id)

    @staticmethod
    def _footnote_markers(citation_refs: list[str], registry: CitationRegistry) -> str:
        numbers = [
            registry.footnote_map()[citation_id]
            for citation_id in citation_refs
            if citation_id in registry.footnote_map()
        ]
        return "".join(f"[{number}]" for number in numbers)

    # ── document-level setup ──────────────────────────────────────────────

    @staticmethod
    def _configure_page(doc: Document, profile: RenderProfile) -> None:
        section = doc.sections[0]
        section.page_width = Mm(profile.page_width_mm)
        section.page_height = Mm(profile.page_height_mm)
        section.top_margin = Mm(profile.margin_top_mm)
        section.bottom_margin = Mm(profile.margin_bottom_mm)
        section.left_margin = Mm(profile.margin_left_mm)
        section.right_margin = Mm(profile.margin_right_mm)

    def _ensure_styles(self, doc: Document, profile: RenderProfile) -> None:
        self._ensure_paragraph_style(doc, profile.citation_note_style)
        self._ensure_paragraph_style(doc, profile.field_label_style)
        self._ensure_paragraph_style(doc, profile.warning_style)
        self._apply_profile_fonts(doc, profile)

    @staticmethod
    def _ensure_paragraph_style(doc: Document, name: str) -> None:
        styles = doc.styles
        try:
            styles[name]
        except KeyError:
            styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)

    @staticmethod
    def _apply_profile_fonts(doc: Document, profile: RenderProfile) -> None:
        """Reference the profile's declared fonts from the base/heading styles.

        DOCX stores font *names* (``w:rFonts``), not glyphs, so this never
        requires a licensed font asset — Word resolves the name at open time.
        The CJK glyph *embedding* + license/hash belongs to the PDF renderer
        (T07), which is separately gated by ``BLOCKED_BY_FONT`` until a
        licensed, hashed CJK font is added.
        """
        DocxRenderer._set_style_fonts(doc.styles["Normal"], profile.body_font, profile.body_font_cjk)
        for level in range(1, 7):
            style_name = f"Heading {level}"
            if style_name in doc.styles:
                DocxRenderer._set_style_fonts(
                    doc.styles[style_name], profile.heading_font, profile.heading_font_cjk
                )

    @staticmethod
    def _set_style_fonts(style, ascii_font: str, east_asia_font: str) -> None:
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:ascii"), ascii_font)
        rfonts.set(qn("w:hAnsi"), ascii_font)
        rfonts.set(qn("w:eastAsia"), east_asia_font)

    def _add_header_footer(self, doc: Document, document: DocumentIR, profile: RenderProfile) -> None:
        section = doc.sections[0]
        header = section.header
        header_paragraph = header.paragraphs[0]
        header_paragraph.text = document.metadata.short_title or document.metadata.title

        footer = section.footer
        footer_paragraph = footer.paragraphs[0]
        footer_paragraph.alignment = 1  # center
        self._add_page_number_field(footer_paragraph)

    @staticmethod
    def _add_page_number_field(paragraph: Paragraph) -> None:
        run = paragraph.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = "PAGE"
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(begin)
        run._r.append(instr)
        run._r.append(end)

    # ── section / block dispatch ───────────────────────────────────────────

    def _render_metadata(self, doc: Document, document: DocumentIR, profile: RenderProfile) -> None:
        meta = document.metadata
        doc.add_heading(meta.title, level=0)
        rows = [
            ("报告编号", meta.report_id),
            ("公司名称", meta.company_name),
            ("法域", meta.jurisdiction),
            ("语言", meta.locale),
            ("报告日期", meta.report_date),
        ]
        rows = [(label, value) for label, value in rows if value]
        if rows:
            table = doc.add_table(rows=len(rows), cols=2)
            table.style = "Table Grid"
            for row_index, (label, value) in enumerate(rows):
                row = table.rows[row_index]
                row.cells[0].text = label
                row.cells[1].text = value

    def _render_section(
        self,
        doc: Document,
        section: SectionIR,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        profile: RenderProfile,
    ) -> None:
        heading = section.title
        if section.ordinal:
            heading = f"{section.ordinal} {section.title}"
        self._add_heading(doc, heading, section.level)
        for block in section.blocks:
            self._render_block(doc, section, block, findings, registry, profile)

    def _render_block(
        self,
        doc: Document,
        section: SectionIR,
        block: Block,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        profile: RenderProfile,
    ) -> None:
        block_type = getattr(block, "type", None)
        if block_type == "paragraph":
            doc.add_paragraph(block.text)
        elif block_type == "claim":
            text = block.text + self._footnote_markers(block.citation_refs, registry)
            doc.add_paragraph(text)
        elif block_type == "list":
            self._render_list(doc, block.items, block.ordered)
        elif block_type == "table":
            self._render_table(doc, block.headers, block.rows)
        elif block_type == "warning":
            label = _WARNING_LABELS.get(block.severity, block.severity)
            paragraph = doc.add_paragraph(f"{label}：{block.text}", style=profile.warning_style)
            paragraph.paragraph_format.keep_with_next = True
        elif block_type == "key_value":
            self._render_table(doc, ["项目", "内容"], [[item.label, item.value] for item in block.items])
        elif block_type == "finding_summary":
            self._render_finding_summary(doc, block, findings)
        elif block_type == "finding_detail":
            self._render_finding_detail(doc, section, block, findings, registry, profile)
        elif block_type == "finding_reference":
            self._render_finding_reference(doc, block, findings)
        elif block_type == "clause_group":
            self._render_clause_group(doc, block)
        elif block_type == "page_break":
            doc.add_page_break()
        elif block_type == "citation_note":
            self._render_citation_note(doc, block, registry, profile)
        else:
            raise DocxRenderError(f"未知 block 类型: {block_type!r}")

    # ── individual block renderers ─────────────────────────────────────────

    @staticmethod
    def _add_heading(doc: Document, text: str, level: int) -> Paragraph:
        heading = doc.add_heading(text, level=min(max(level, 1), 6))
        heading.paragraph_format.keep_with_next = True
        return heading

    @staticmethod
    def _render_list(doc: Document, items: list[ListItem], ordered: bool, depth: int = 0) -> None:
        style = "List Number" if ordered else "List Bullet"
        for item in items:
            paragraph = doc.add_paragraph(item.text, style=style)
            paragraph.paragraph_format.left_indent = Pt(12 * (depth + 1))
            if item.children:
                DocxRenderer._render_list(doc, item.children, ordered, depth + 1)

    def _render_table(self, doc: Document, headers: list[str], rows: list[list[str]]) -> None:
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = "Table Grid"
        self._set_table_header_repeat(table.rows[0])
        for column, header in enumerate(headers):
            table.rows[0].cells[column].text = header
        for row_index, row in enumerate(rows, start=1):
            for column, value in enumerate(row[: len(headers)]):
                table.rows[row_index].cells[column].text = value

    def _render_finding_summary(
        self, doc: Document, block: FindingSummaryBlock, findings: dict[str, FindingRecord]
    ) -> None:
        headers = [_SUMMARY_LABELS.get(column, column) for column in block.columns]
        rows: list[list[str]] = []
        for ref in block.finding_refs:
            finding = findings.get(ref)
            if finding is None:
                raise DocxRenderError(f"finding_summary 引用未注册的 finding: {ref}")
            rows.append([self._summary_cell(column, finding) for column in block.columns])
        self._render_table(doc, headers, rows)

    @staticmethod
    def _summary_cell(column: str, finding: FindingRecord) -> str:
        value = getattr(finding, column, "")
        return "" if value is None else str(value)

    def _render_finding_detail(
        self,
        doc: Document,
        section: SectionIR,
        block: FindingDetailBlock,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        profile: RenderProfile,
    ) -> None:
        finding = findings.get(block.finding_ref)
        if finding is None:
            raise DocxRenderError(f"finding_detail 引用未注册的 finding: {block.finding_ref}")
        level = min(section.level + 1, 6)
        self._add_heading(doc, f"{finding.finding_id} {finding.title}", level)
        for field in block.field_order:
            if field == "legal_basis":
                content_lines = self._legal_basis_lines(finding, registry)
            else:
                content = self._field_content(field, finding)
                content_lines = None if content is None else [content]
            if content_lines is None:
                continue
            self._add_field_block(doc, field, content_lines, profile)

    @staticmethod
    def _add_field_block(doc: Document, field: str, lines: list[str], profile: RenderProfile) -> None:
        label_paragraph = doc.add_paragraph(style=profile.field_label_style)
        label_run = label_paragraph.add_run(_FIELD_LABELS.get(field, field))
        label_run.bold = True
        label_paragraph.paragraph_format.keep_with_next = True
        for line in lines:
            doc.add_paragraph(line)

    def _legal_basis_lines(
        self, finding: FindingRecord, registry: CitationRegistry
    ) -> list[str] | None:
        """Render legal basis one entry per line (I068-22).

        ``basis_entries`` is authoritative when present: each entry carries its
        label, an optional footnote marker for its ``citation_ref``, and the
        attributed rationale. Pure-label entries keep only the label. Modules
        without ``basis_entries`` (e.g. BCR) fall back to the ``legal_basis``
        shim unchanged.
        """
        if finding.basis_entries:
            lines: list[str] = []
            for basis in finding.basis_entries:
                marker = (
                    self._footnote_markers([basis.citation_ref], registry)
                    if basis.citation_ref
                    else ""
                )
                head = f"{basis.label}{marker}"
                lines.append(f"{head}：{basis.rationale}" if basis.rationale else head)
            return lines or None
        labels = "；".join(finding.legal_basis)
        markers = self._footnote_markers(finding.citation_refs, registry)
        return [labels + markers] if (labels or markers) else None

    def _field_content(self, field: str, finding: FindingRecord) -> str | None:
        if field == "statement":
            return finding.statement
        if field == "recommendation":
            return finding.recommendation or None
        if field == "suggested_revision":
            return finding.suggested_revision or None
        value = getattr(finding, field, None)
        return str(value) if value else None

    def _render_finding_reference(
        self, doc: Document, block: FindingReferenceBlock, findings: dict[str, FindingRecord]
    ) -> None:
        finding = findings.get(block.finding_ref)
        if finding is None:
            raise DocxRenderError(f"finding_reference 引用未注册的 finding: {block.finding_ref}")
        note = f"：{block.note}" if block.note else ""
        doc.add_paragraph(f"参见 {finding.finding_id} {finding.title}{note}")

    def _render_clause_group(self, doc: Document, block: ClauseGroupBlock) -> None:
        doc.add_paragraph(block.title)
        depth_formats = self._collect_depth_formats(block.clauses)
        if depth_formats:
            num_id = self._ensure_clause_numbering(doc, depth_formats)
            for position, clause in enumerate(block.clauses, start=1):
                self._render_clause(doc, clause, position, depth=0, num_id=num_id)
        else:
            for clause in block.clauses:
                self._render_clause_plain(doc, clause)

    @classmethod
    def _collect_depth_formats(cls, clauses: list[ClauseNode]) -> list[str]:
        """Map each depth to its numbering style (first non-``none`` node wins).

        The returned list is depth-indexed; a depth whose nodes are all ``none``
        keeps the ``decimal`` placeholder (unused, because ``_render_clause``
        skips numbering for ``none`` nodes).
        """
        formats: list[str] = []

        def walk(nodes: list[ClauseNode], depth: int) -> None:
            while len(formats) <= depth:
                formats.append("decimal")
            if formats[depth] == "decimal":
                for node in nodes:
                    if node.numbering_style != "none":
                        formats[depth] = node.numbering_style
                        break
            for node in nodes:
                walk(node.children, depth + 1)

        walk(clauses, 0)
        return formats

    def _render_clause(self, doc: Document, clause: ClauseNode, position: int, depth: int, num_id: int) -> None:
        paragraph = doc.add_paragraph(clause.text)
        if clause.numbering_style != "none":
            self._apply_numbering(paragraph, num_id, depth)
        for child_position, child in enumerate(clause.children, start=1):
            self._render_clause(doc, child, child_position, depth + 1, num_id)

    def _render_clause_plain(self, doc: Document, clause: ClauseNode, depth: int = 0) -> None:
        paragraph = doc.add_paragraph(clause.text)
        paragraph.paragraph_format.left_indent = Pt(12 * (depth + 1))
        for child in clause.children:
            self._render_clause_plain(doc, child, depth + 1)

    def _ensure_clause_numbering(self, doc: Document, depth_formats: list[str]) -> int:
        numbering = doc.part.numbering_part.element
        max_abstract = max(
            (int(el.get(qn("w:abstractNumId")) or 0) for el in numbering.findall(qn("w:abstractNum"))),
            default=-1,
        )
        max_num = max(
            (int(el.get(qn("w:numId")) or 0) for el in numbering.findall(qn("w:num"))),
            default=-1,
        )
        abstract_id = max_abstract + 1
        num_id = max_num + 1

        levels = []
        for depth, style in enumerate(depth_formats[: _MAX_CLAUSE_DEPTH]):
            num_fmt = _NUMFMT_BY_STYLE.get(style)
            if num_fmt is None:
                continue
            placeholder = f"%{depth + 1}"
            lvl_text = f"({placeholder})" if style == "lower_alpha" else f"{placeholder}."
            levels.append(
                f'<w:lvl w:ilvl="{depth}">'
                f'<w:start w:val="1"/>'
                f'<w:numFmt w:val="{num_fmt}"/>'
                f'<w:lvlText w:val="{lvl_text}"/>'
                f'<w:lvlJc w:val="left"/>'
                f'<w:pPr><w:ind w:left="{720 * (depth + 1)}" w:hanging="360"/></w:pPr>'
                f'</w:lvl>'
            )

        abstract = parse_xml(
            f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">'
            f'<w:multiLevelType w:val="multilevel"/>'
            + "".join(levels)
            + "</w:abstractNum>"
        )
        num = parse_xml(
            f'<w:num {nsdecls("w")} w:numId="{num_id}">'
            f'<w:abstractNumId w:val="{abstract_id}"/>'
            f'</w:num>'
        )
        numbering.append(abstract)
        numbering.append(num)
        return num_id

    @staticmethod
    def _apply_numbering(paragraph: Paragraph, num_id: int, ilvl: int) -> None:
        p_pr = paragraph._p.get_or_add_pPr()
        num_pr = OxmlElement("w:numPr")
        ilvl_el = OxmlElement("w:ilvl")
        ilvl_el.set(qn("w:val"), str(ilvl))
        num_id_el = OxmlElement("w:numId")
        num_id_el.set(qn("w:val"), str(num_id))
        num_pr.append(ilvl_el)
        num_pr.append(num_id_el)
        p_pr.append(num_pr)

    @staticmethod
    def _set_table_header_repeat(row: _Row) -> None:
        tr_pr = row._tr.get_or_add_trPr()
        tbl_header = OxmlElement("w:tblHeader")
        tbl_header.set(qn("w:val"), "true")
        tr_pr.append(tbl_header)

    def _render_citation_note(
        self, doc: Document, block: CitationNoteBlock, registry: CitationRegistry, profile: RenderProfile
    ) -> None:
        for citation_id in block.citation_refs:
            record = registry.resolve(citation_id)
            if record is None:
                raise DocxRenderError(f"citation_note 引用未注册的 citation: {citation_id}")
            number = registry.footnote_map().get(citation_id)
            label = self._format_citation(record)
            text = f"{number}. {label}" if number is not None else f"- {label}"
            doc.add_paragraph(text, style=profile.citation_note_style)

    @staticmethod
    def _format_citation(record: CitationRecord) -> str:
        parts = [record.title]
        locator = record.locator
        if locator is not None:
            if locator.article:
                parts.append(f"Article {locator.article}")
            if locator.paragraph:
                parts.append(f"paragraph {locator.paragraph}")
            if locator.item:
                parts.append(f"item {locator.item}")
        return " — ".join(parts)


def _normalize_zip_timestamps(blob: bytes) -> bytes:
    """Re-pack a ZIP (DOCX) with a fixed entry timestamp for byte determinism.

    ``python-docx`` stamps each zip entry with ``time.localtime()`` (second
    resolution), so two renders that straddle a second boundary produce
    different bytes. Re-packing every entry with a fixed ``date_time`` makes
    ``render_docx`` deterministic, which the render manifest's SHA-256 stability
    gate depends on.
    """
    import zipfile

    from io import BytesIO

    source = zipfile.ZipFile(BytesIO(blob))
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            zinfo = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.external_attr = info.external_attr
            zinfo.create_system = info.create_system
            target.writestr(zinfo, source.read(info.filename))
    return output.getvalue()


def render_docx(document: DocumentIR, registry: CitationRegistry | None = None) -> bytes:
    """Convenience entry point: render a DocumentIR to an in-memory DOCX."""
    return DocxRenderer().render(document, registry)


def render_docx_to_file(
    document: DocumentIR, output_path: Path, registry: CitationRegistry | None = None
) -> Path:
    """Convenience entry point: render a DocumentIR to a ``.docx`` file."""
    return DocxRenderer().render_to_file(document, output_path, registry)


__all__ = ["DocxRenderer", "DocxRenderError", "render_docx", "render_docx_to_file"]
