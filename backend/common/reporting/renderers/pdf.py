"""IR → PDF fixed-layout renderer (task067 T06).

Renders a deliverable PDF directly from a v4 ``DocumentIR`` — never through the
legacy Markdown parser. The layout contract:

- fonts are registered *explicitly*: a CJK font (embedded when a licensed,
  hashed asset is tracked, otherwise degraded to the non-embedded
  ``STSong-Light`` CID font) and a redistributable Latin font (Liberation Sans,
  ``emb=yes``);
- ``BaseDocTemplate`` + ``PageTemplate`` + ``onPage`` draw the running header
  and a live page-number footer;
- the finding summary is a short table (≤ 4 columns) with a repeated header;
- finding detail is vertical: a keep-with-next heading, then bold field labels
  each kept with their content paragraph;
- ``ClauseNode`` trees render explicit multi-level legal numbering with
  recursive indentation;
- the citation appendix renders as ordinary copyable/searchable paragraphs.

Unknown block types and unknown render profiles raise :class:`PdfRenderError`
(fail-closed). This renderer never calls the legacy
``_markdown_to_flowables()``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from backend.common.reporting.render_profiles import (
    FontAsset,
    RenderProfile,
    get_cjk_font,
    get_latin_font,
    get_profile,
)
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
    ListItem as IRListItem,
    SectionIR,
)
from backend.common.reporting.schema.citations import CitationRecord, CitationRegistry


class PdfRenderError(RuntimeError):
    """Raised when a DocumentIR cannot be rendered to PDF."""


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

_ROMAN = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)


def _to_roman(value: int) -> str:
    result = ""
    remainder = value
    for numeral, symbol in _ROMAN:
        while remainder >= numeral:
            result += symbol
            remainder -= numeral
    return result


def _clause_number_token(style: str, position: int) -> str:
    if style == "decimal":
        return f"{position}."
    if style == "lower_alpha":
        return f"({chr(96 + position)})"
    if style == "lower_roman":
        return f"{_to_roman(position).lower()}."
    return ""  # "none"


@dataclass(frozen=True)
class FontSpec:
    """Registered reportlab font names + whether the CJK font embeds."""

    body: str
    body_bold: str
    latin: str
    latin_bold: str
    cjk_embedded: bool
    cjk_asset: FontAsset | None


class PdfRenderer:
    """Render a v4 ``DocumentIR`` into an in-memory PDF."""

    def render(self, document: DocumentIR, registry: CitationRegistry | None = None) -> bytes:
        registry = registry or CitationRegistry(document.citations)
        profile = get_profile(document.render_contract.profile_id)
        findings = {finding.finding_id: finding for finding in document.findings}
        self._assign_citation_numbers(document, registry)
        fonts = self._register_fonts()

        # Deterministic output: reportlab's ``invariant`` mode fixes the PDF
        # ``/CreationDate`` and ``/ID`` digest so the byte-for-byte hash is
        # stable across runs (a precondition for the render_manifest hash).
        rl_config.invariant = True

        buffer = BytesIO()
        doc = self._build_template(buffer, document, profile, fonts)
        story = self._build_story(document, findings, registry, profile, fonts)
        doc.build(story)
        return buffer.getvalue()

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

    # ── font registration ─────────────────────────────────────────────────

    def _register_fonts(self) -> FontSpec:
        latin = get_latin_font()
        latin_name = "LiberationSans"
        latin_bold_name = "LiberationSans-Bold"
        if latin is not None:
            self._register_ttf(latin_name, _ROOT / latin.path)
        else:
            latin_name = "Helvetica"

        bold_asset = _find_latin_bold()
        if bold_asset is not None:
            self._register_ttf(latin_bold_name, _ROOT / bold_asset.path)
        else:
            latin_bold_name = latin_name

        cjk = get_cjk_font()
        if cjk is not None:
            cjk_name = "ReportCJK"
            self._register_ttf(cjk_name, _ROOT / cjk.path)
            cjk_embedded = True
            cjk_bold = cjk_name
        else:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            cjk_name = "STSong-Light"
            cjk_embedded = False
            cjk_bold = cjk_name

        return FontSpec(
            body=cjk_name,
            body_bold=cjk_bold,
            latin=latin_name,
            latin_bold=latin_bold_name,
            cjk_embedded=cjk_embedded,
            cjk_asset=cjk,
        )

    @staticmethod
    def _register_ttf(name: str, path: Path) -> None:
        # ReportLab raises on a missing/invalid font; fail-closed.
        pdfmetrics.registerFont(TTFont(name, str(path)))

    # ── template / page geometry ──────────────────────────────────────────

    def _build_template(
        self, buffer: BytesIO, document: DocumentIR, profile: RenderProfile, fonts: FontSpec
    ) -> BaseDocTemplate:
        page_width = profile.page_width_mm * mm
        page_height = profile.page_height_mm * mm
        left = profile.margin_left_mm * mm
        right = profile.margin_right_mm * mm
        top = profile.margin_top_mm * mm
        bottom = profile.margin_bottom_mm * mm

        doc = BaseDocTemplate(
            buffer,
            pagesize=(page_width, page_height),
            leftMargin=left,
            rightMargin=right,
            topMargin=top,
            bottomMargin=bottom,
            title=document.metadata.title,
        )
        header_text = document.metadata.short_title or document.metadata.title
        frame = Frame(left, bottom, page_width - left - right, page_height - top - bottom, id="body")

        def on_page(canvas, _doc) -> None:
            self._draw_page_chrome(canvas, _doc, header_text, profile, fonts)

        template = PageTemplate(id="report", frames=[frame], onPage=on_page)
        doc.addPageTemplates([template])
        return doc

    def _draw_page_chrome(self, canvas, doc, header_text: str, profile: RenderProfile, fonts: FontSpec) -> None:
        canvas.saveState()
        page_width, page_height = A4
        # Running header (top-left, thin rule below).
        canvas.setFont(fonts.body, 9)
        canvas.drawString(profile.margin_left_mm * mm, page_height - 12 * mm, header_text[:64])
        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.line(
            profile.margin_left_mm * mm,
            page_height - 14 * mm,
            page_width - profile.margin_right_mm * mm,
            page_height - 14 * mm,
        )
        # Footer page number (digits only → Latin font embeds cleanly).
        canvas.setFont(fonts.latin, 9)
        canvas.drawCentredString(page_width / 2, 12 * mm, str(doc.page))
        canvas.restoreState()

    # ── story construction ────────────────────────────────────────────────

    def _build_story(
        self,
        document: DocumentIR,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        profile: RenderProfile,
        fonts: FontSpec,
    ) -> list:
        styles = self._build_styles(profile, fonts)
        story: list = [
            Paragraph(_escape(document.metadata.title), styles["title"]),
            Spacer(1, 8),
        ]
        for section in document.sections:
            self._render_section(story, section, findings, registry, profile, fonts, styles)
        return story

    def _build_styles(self, profile: RenderProfile, fonts: FontSpec) -> dict[str, ParagraphStyle]:
        base_size = profile.base_font_size_pt
        base = ParagraphStyle(
            "Base",
            fontName=fonts.body,
            fontSize=base_size,
            leading=base_size * 1.5,
            textColor=colors.HexColor("#1f2937"),
        )
        heading = ParagraphStyle(
            "Heading",
            parent=base,
            fontName=fonts.body_bold,
            fontSize=base_size + 3,
            leading=(base_size + 3) * 1.4,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=6,
            spaceAfter=3,
            keepWithNext=1,
        )
        subheading = ParagraphStyle(
            "Subheading",
            parent=heading,
            fontSize=base_size + 1.5,
            leading=(base_size + 1.5) * 1.4,
            spaceBefore=4,
            spaceAfter=2,
        )
        field_label = ParagraphStyle(
            "FieldLabel",
            parent=base,
            fontName=fonts.body_bold,
            spaceBefore=4,
            spaceAfter=1,
            keepWithNext=1,
        )
        warning = ParagraphStyle(
            "Warning",
            parent=base,
            textColor=colors.HexColor("#92400e"),
            backColor=colors.HexColor("#fef3c7"),
            borderColor=colors.HexColor("#f59e0b"),
            borderWidth=0.6,
            borderPadding=5,
            spaceBefore=4,
            spaceAfter=4,
        )
        citation = ParagraphStyle(
            "Citation",
            parent=base,
            fontSize=base_size - 1,
            leading=(base_size - 1) * 1.4,
            textColor=colors.HexColor("#374151"),
            spaceBefore=1,
            spaceAfter=1,
        )
        return {
            "title": ParagraphStyle(
                "Title", parent=heading, fontName=fonts.body_bold,
                fontSize=base_size + 7, leading=(base_size + 7) * 1.3,
                spaceAfter=8, keepWithNext=1,
            ),
            "h1": heading,
            "h2": subheading,
            "h3": ParagraphStyle("H3", parent=subheading, fontSize=base_size + 0.5),
            "p": base,
            "li": ParagraphStyle("LI", parent=base, leftIndent=6, spaceBefore=1, spaceAfter=1),
            "field_label": field_label,
            "warning": warning,
            "citation": citation,
        }

    # ── citation numbering (first-use order, mirroring the compiler) ──────

    @staticmethod
    def _iter_clause_nodes(clauses: list[ClauseNode]) -> Iterator[ClauseNode]:
        for clause in clauses:
            yield clause
            yield from PdfRenderer._iter_clause_nodes(clause.children)

    @staticmethod
    def _iter_citation_refs(document: DocumentIR) -> Iterator[str]:
        for section in document.sections:
            for block in section.blocks:
                for citation_id in getattr(block, "citation_refs", []):
                    yield citation_id
                for clause in PdfRenderer._iter_clause_nodes(getattr(block, "clauses", [])):
                    for citation_id in clause.citation_refs:
                        yield citation_id
        for finding in document.findings:
            for citation_id in finding.citation_refs:
                yield citation_id

    @staticmethod
    def _assign_citation_numbers(document: DocumentIR, registry: CitationRegistry) -> None:
        for citation_id in PdfRenderer._iter_citation_refs(document):
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

    # ── section / block dispatch ───────────────────────────────────────────

    def _render_section(
        self,
        story: list,
        section: SectionIR,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        profile: RenderProfile,
        fonts: FontSpec,
        styles: dict[str, ParagraphStyle],
    ) -> None:
        heading = section.title
        if section.ordinal:
            heading = f"{section.ordinal} {section.title}"
        style = styles["h1"] if section.level <= 1 else styles["h2"] if section.level == 2 else styles["h3"]
        story.append(Paragraph(_escape(heading), style))
        for block in section.blocks:
            self._render_block(story, section, block, findings, registry, profile, fonts, styles)

    def _render_block(
        self,
        story: list,
        section: SectionIR,
        block: Block,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        profile: RenderProfile,
        fonts: FontSpec,
        styles: dict[str, ParagraphStyle],
    ) -> None:
        block_type = getattr(block, "type", None)
        if block_type == "paragraph":
            story.append(Paragraph(_escape(block.text), styles["p"]))
        elif block_type == "claim":
            text = block.text + self._footnote_markers(block.citation_refs, registry)
            story.append(Paragraph(_escape(text), styles["p"]))
        elif block_type == "list":
            story.extend(self._render_list(block.items, block.ordered, styles))
        elif block_type == "table":
            story.append(self._render_table(block.headers, block.rows, styles))
        elif block_type == "warning":
            label = _WARNING_LABELS.get(block.severity, block.severity)
            story.append(Paragraph(_escape(f"{label}：{block.text}"), styles["warning"]))
        elif block_type == "key_value":
            story.append(self._render_table(["项目", "内容"], [[item.label, item.value] for item in block.items], styles))
        elif block_type == "finding_summary":
            story.append(self._render_finding_summary(block, findings, styles))
        elif block_type == "finding_detail":
            self._render_finding_detail(story, section, block, findings, registry, styles)
        elif block_type == "finding_reference":
            self._render_finding_reference(story, block, findings, styles)
        elif block_type == "clause_group":
            self._render_clause_group(story, block, styles)
        elif block_type == "page_break":
            story.append(PageBreak())
        elif block_type == "citation_note":
            self._render_citation_note(story, block, registry, styles)
        else:
            raise PdfRenderError(f"未知 block 类型: {block_type!r}")

    # ── individual block renderers ─────────────────────────────────────────

    def _render_list(self, items: list[IRListItem], ordered: bool, styles: dict[str, ParagraphStyle]) -> list:
        """Render a list as explicit, indentation-based paragraphs.

        ReportLab's ``ListFlowable`` cannot preserve multi-level legal identity
        (nested lists restart their own numbering), so — as with clauses — the
        renderer writes the marker itself and indents by depth. This keeps the
        text layer deterministic and copyable.
        """
        flowables: list = []
        self._flatten_list(flowables, items, ordered, depth=0, styles=styles)
        return flowables

    def _flatten_list(
        self,
        out: list,
        items: list[IRListItem],
        ordered: bool,
        depth: int,
        styles: dict[str, ParagraphStyle],
    ) -> None:
        for index, item in enumerate(items, start=1):
            marker = f"{index}." if ordered else "•"
            style = ParagraphStyle(
                f"LI{depth}",
                parent=styles["li"],
                leftIndent=6 + depth * 10,
                spaceBefore=1,
                spaceAfter=1,
            )
            out.append(Paragraph(_escape(f"{marker} {item.text}"), style))
            if item.children:
                self._flatten_list(out, item.children, ordered, depth + 1, styles)

    def _render_table(self, headers: list[str], rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
        cell_style = ParagraphStyle("Cell", parent=styles["p"], fontSize=styles["p"].fontSize - 0.5)
        header_style = ParagraphStyle("CellHeader", parent=cell_style, fontName=styles["p"].fontName, spaceAfter=0)
        data = [[Paragraph(_escape(h), header_style) for h in headers]]
        for row in rows:
            data.append([Paragraph(_escape(cell), cell_style) for cell in row[: len(headers)]])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#d0d7de")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5ff")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    def _render_finding_summary(
        self, block: FindingSummaryBlock, findings: dict[str, FindingRecord], styles: dict[str, ParagraphStyle]
    ) -> Table:
        headers = [_SUMMARY_LABELS.get(column, column) for column in block.columns]
        rows: list[list[str]] = []
        for ref in block.finding_refs:
            finding = findings.get(ref)
            if finding is None:
                raise PdfRenderError(f"finding_summary 引用未注册的 finding: {ref}")
            rows.append([self._summary_cell(column, finding) for column in block.columns])
        return self._render_table(headers, rows, styles)

    @staticmethod
    def _summary_cell(column: str, finding: FindingRecord) -> str:
        value = getattr(finding, column, "")
        return "" if value is None else str(value)

    def _render_finding_detail(
        self,
        story: list,
        section: SectionIR,
        block: FindingDetailBlock,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        styles: dict[str, ParagraphStyle],
    ) -> None:
        finding = findings.get(block.finding_ref)
        if finding is None:
            raise PdfRenderError(f"finding_detail 引用未注册的 finding: {block.finding_ref}")
        style = styles["h2"] if section.level <= 1 else styles["h3"]
        story.append(Paragraph(_escape(f"{finding.finding_id} {finding.title}"), style))
        for field in block.field_order:
            if field == "legal_basis":
                content_lines = self._legal_basis_lines(finding, registry)
            else:
                content = self._field_content(field, finding)
                content_lines = None if content is None else [content]
            if content_lines is None:
                continue
            story.append(Paragraph(_escape(_FIELD_LABELS.get(field, field)), styles["field_label"]))
            for line in content_lines:
                story.append(Paragraph(_escape(line), styles["p"]))

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
        self,
        story: list,
        block: FindingReferenceBlock,
        findings: dict[str, FindingRecord],
        styles: dict[str, ParagraphStyle],
    ) -> None:
        finding = findings.get(block.finding_ref)
        if finding is None:
            raise PdfRenderError(f"finding_reference 引用未注册的 finding: {block.finding_ref}")
        note = f"：{block.note}" if block.note else ""
        story.append(Paragraph(_escape(f"参见 {finding.finding_id} {finding.title}{note}"), styles["p"]))

    def _render_clause_group(self, story: list, block: ClauseGroupBlock, styles: dict[str, ParagraphStyle]) -> None:
        story.append(Paragraph(_escape(block.title), styles["h2"]))
        for position, clause in enumerate(block.clauses, start=1):
            self._render_clause(story, clause, position, depth=0, styles=styles)

    def _render_clause(self, story: list, clause: ClauseNode, position: int, depth: int, styles: dict[str, ParagraphStyle]) -> None:
        token = _clause_number_token(clause.numbering_style, position)
        heading = f"{token} {clause.text}".strip()
        style = ParagraphStyle(
            f"Clause{depth}",
            parent=styles["p"],
            leftIndent=8 + depth * 10,
            spaceBefore=1,
            spaceAfter=1,
        )
        story.append(Paragraph(_escape(heading), style))
        for child_position, child in enumerate(clause.children, start=1):
            self._render_clause(story, child, child_position, depth + 1, styles)

    def _render_citation_note(
        self,
        story: list,
        block: CitationNoteBlock,
        registry: CitationRegistry,
        styles: dict[str, ParagraphStyle],
    ) -> None:
        for citation_id in block.citation_refs:
            record = registry.resolve(citation_id)
            if record is None:
                raise PdfRenderError(f"citation_note 引用未注册的 citation: {citation_id}")
            number = registry.footnote_map().get(citation_id)
            label = self._format_citation(record)
            text = f"{number}. {label}" if number is not None else f"- {label}"
            story.append(Paragraph(_escape(text), styles["citation"]))

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


_ROOT = Path(__file__).resolve().parents[4]


def _find_latin_bold() -> FontAsset | None:
    from backend.common.reporting.render_profiles import discover_font_assets

    for asset in discover_font_assets():
        if not asset.covers_cjk and "bold" in asset.path.lower():
            return asset
    return None


def _escape(text: str) -> str:
    """Escape reportlab Paragraph markup while keeping semantic text intact."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_pdf(document: DocumentIR, registry: CitationRegistry | None = None) -> bytes:
    """Convenience entry point: render a DocumentIR to an in-memory PDF."""
    return PdfRenderer().render(document, registry)


def render_pdf_to_file(
    document: DocumentIR, output_path: Path, registry: CitationRegistry | None = None
) -> Path:
    """Convenience entry point: render a DocumentIR to a ``.pdf`` file."""
    return PdfRenderer().render_to_file(document, output_path, registry)


__all__ = ["PdfRenderer", "PdfRenderError", "FontSpec", "render_pdf", "render_pdf_to_file"]
