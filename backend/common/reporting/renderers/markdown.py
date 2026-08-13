"""IR → Markdown renderer (task067 T03).

The renderer reads *only* the ``DocumentIR`` (plus the per-document citation
registry it needs to resolve stable citation IDs into first-use footnote
numbers). It never touches the legacy BCR Markdown template or ``chapter``
content, and it emits only structural Markdown — headings, tables, lists,
blockquotes and plain paragraphs. Emphasis markers (``**``/``__``) and
``{{CIT-*}}`` residues are forbidden by the compiler's render gate, so this
renderer deliberately avoids both.

Design invariants:

- one heading per ``SectionIR`` (level mapped 1:1 to ``#``);
- a finding summary renders a short table, never the six-column detail table;
- a finding detail renders field blocks (statement/legal basis/recommendation/
  suggested revision) rather than a flattened paragraph;
- ``ClauseNode`` numbering is expressed in the output as explicit legal
  numbering (``1.``/``(a)``/``i.``) with recursive indentation — it is *not*
  handed off to Markdown's own list renumbering, which would lose multi-level
  legal identity;
- unknown block types raise ``RenderError`` (fail-closed).
"""

from __future__ import annotations

from collections.abc import Iterator

from backend.common.reporting.schema import (
    Block,
    CitationNoteBlock,
    ClaimBlock,
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


class RenderError(RuntimeError):
    """Raised when a DocumentIR cannot be rendered to Markdown."""


# ── numbering helpers ───────────────────────────────────────────────────────

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


def _escape_cell(value: str) -> str:
    """Escape pipe/line-break so a semantic value cannot break a Markdown table."""
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


class MarkdownRenderer:
    """Render a v4 ``DocumentIR`` into deterministic Markdown."""

    def render(self, document: DocumentIR, registry: CitationRegistry | None = None) -> str:
        registry = registry or CitationRegistry(document.citations)
        findings = {finding.finding_id: finding for finding in document.findings}
        self._assign_citation_numbers(document, registry)

        rendered: list[str] = []
        for section in document.sections:
            self._render_section(section, findings, registry, rendered)

        text = "\n".join(rendered).rstrip() + "\n"
        self._assert_no_residue(text)
        return text

    # ── citation numbering (first-use order, mirroring the compiler) ──────

    @staticmethod
    def _iter_clause_nodes(clauses: list[ClauseNode]) -> Iterator[ClauseNode]:
        for clause in clauses:
            yield clause
            yield from MarkdownRenderer._iter_clause_nodes(clause.children)

    @staticmethod
    def _iter_citation_refs(document: DocumentIR) -> Iterator[str]:
        for section in document.sections:
            for block in section.blocks:
                for citation_id in getattr(block, "citation_refs", []):
                    yield citation_id
                for clause in MarkdownRenderer._iter_clause_nodes(
                    getattr(block, "clauses", [])
                ):
                    for citation_id in clause.citation_refs:
                        yield citation_id
        for finding in document.findings:
            for citation_id in finding.citation_refs:
                yield citation_id

    @staticmethod
    def _assign_citation_numbers(document: DocumentIR, registry: CitationRegistry) -> None:
        for citation_id in MarkdownRenderer._iter_citation_refs(document):
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
        section: SectionIR,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        out: list[str],
    ) -> None:
        if out:
            out.append("")
        heading = section.title
        if section.ordinal:
            heading = f"{section.ordinal} {section.title}"
        out.append(f"{'#' * section.level} {heading}")
        out.append("")
        for block in section.blocks:
            self._render_block(section, block, findings, registry, out)

    def _render_block(
        self,
        section: SectionIR,
        block: Block,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
        out: list[str],
    ) -> None:
        block_type = getattr(block, "type", None)
        if block_type == "paragraph":
            out.append(block.text)
            out.append("")
        elif block_type == "claim":
            out.append(self._render_claim(block, registry))
            out.append("")
        elif block_type == "list":
            out.extend(self._render_list(block.items, block.ordered))
            out.append("")
        elif block_type == "table":
            out.extend(self._render_table(block.headers, block.rows))
            out.append("")
        elif block_type == "warning":
            label = _WARNING_LABELS.get(block.severity, block.severity)
            out.append(f"> {label}：{block.text}")
            out.append("")
        elif block_type == "key_value":
            out.extend(self._render_table(
                ["项目", "内容"],
                [[item.label, item.value] for item in block.items],
            ))
            out.append("")
        elif block_type == "finding_summary":
            out.extend(self._render_finding_summary(block, findings))
            out.append("")
        elif block_type == "finding_detail":
            out.extend(self._render_finding_detail(section, block, findings, registry))
        elif block_type == "finding_reference":
            out.extend(self._render_finding_reference(block, findings))
        elif block_type == "clause_group":
            out.extend(self._render_clause_group(block))
            out.append("")
        elif block_type == "page_break":
            out.append(f"<!-- page-break: {block.reason} -->")
            out.append("")
        elif block_type == "citation_note":
            out.extend(self._render_citation_note(block, registry))
            out.append("")
        else:
            raise RenderError(f"未知 block 类型: {block_type!r}")

    # ── individual block renderers ─────────────────────────────────────────

    def _render_claim(self, block: ClaimBlock, registry: CitationRegistry) -> str:
        text = block.text
        markers = self._footnote_markers(block.citation_refs, registry)
        if markers:
            text = f"{text}{markers}"
        return text

    @staticmethod
    def _render_list(items: list[ListItem], ordered: bool, depth: int = 0) -> list[str]:
        lines: list[str] = []
        indent = "    " * depth
        for index, item in enumerate(items, start=1):
            marker = f"{index}." if ordered else "-"
            lines.append(f"{indent}{marker} {item.text}")
            if item.children:
                lines.extend(MarkdownRenderer._render_list(item.children, ordered, depth + 1))
        return lines

    @staticmethod
    def _render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
        lines = ["| " + " | ".join(_escape_cell(h) for h in headers) + " |"]
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            lines.append("| " + " | ".join(_escape_cell(c) for c in row) + " |")
        return lines

    def _render_finding_summary(
        self, block: FindingSummaryBlock, findings: dict[str, FindingRecord]
    ) -> list[str]:
        headers = [_SUMMARY_LABELS.get(column, column) for column in block.columns]
        rows: list[list[str]] = []
        for ref in block.finding_refs:
            finding = findings.get(ref)
            if finding is None:
                raise RenderError(f"finding_summary 引用未注册的 finding: {ref}")
            rows.append([self._summary_cell(column, finding) for column in block.columns])
        return self._render_table(headers, rows)

    @staticmethod
    def _summary_cell(column: str, finding: FindingRecord) -> str:
        value = getattr(finding, column, "")
        return "" if value is None else str(value)

    def _render_finding_detail(
        self,
        section: SectionIR,
        block: FindingDetailBlock,
        findings: dict[str, FindingRecord],
        registry: CitationRegistry,
    ) -> list[str]:
        finding = findings.get(block.finding_ref)
        if finding is None:
            raise RenderError(f"finding_detail 引用未注册的 finding: {block.finding_ref}")

        level = min(section.level + 1, 6)
        lines = [f"{'#' * level} {finding.finding_id} {finding.title}", ""]

        for field in block.field_order:
            if field == "legal_basis":
                content_lines = self._legal_basis_lines(finding, registry)
            else:
                content = self._field_content(field, finding)
                content_lines = None if content is None else [content]
            if content_lines is None:
                continue
            if len(content_lines) == 1:
                lines.append(f"{_FIELD_LABELS.get(field, field)}：{content_lines[0]}")
                lines.append("")
            else:
                lines.append(f"{_FIELD_LABELS.get(field, field)}：")
                for item in content_lines:
                    lines.append(f"- {item}")
                lines.append("")
        return lines

    def _legal_basis_lines(
        self, finding: FindingRecord, registry: CitationRegistry
    ) -> list[str] | None:
        """Render legal basis one entry per line.

        ``basis_entries`` is authoritative when present: each entry carries a
        human-readable label, an optional footnote marker resolving its
        ``citation_ref``, and the attributed rationale. Pure-label entries (no
        ``citation_ref``) keep only the label. Modules without ``basis_entries``
        (e.g. BCR) fall back to the ``legal_basis`` shim unchanged.
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
        self, block: FindingReferenceBlock, findings: dict[str, FindingRecord]
    ) -> list[str]:
        finding = findings.get(block.finding_ref)
        if finding is None:
            raise RenderError(f"finding_reference 引用未注册的 finding: {block.finding_ref}")
        note = f"：{block.note}" if block.note else ""
        return [f"> 参见 {finding.finding_id} {finding.title}{note}", ""]

    def _render_clause_group(self, block: ClauseGroupBlock) -> list[str]:
        lines = [block.title, ""]
        for position, clause in enumerate(block.clauses, start=1):
            lines.extend(self._render_clause(clause, position, depth=0))
        return lines

    def _render_clause(self, clause: ClauseNode, position: int, depth: int) -> list[str]:
        indent = "  " * depth
        token = _clause_number_token(clause.numbering_style, position)
        heading = f"{token} {clause.text}".strip()
        lines = [f"{indent}{heading}"]
        for child_position, child in enumerate(clause.children, start=1):
            lines.extend(self._render_clause(child, child_position, depth + 1))
        return lines

    def _render_citation_note(
        self, block: CitationNoteBlock, registry: CitationRegistry
    ) -> list[str]:
        lines: list[str] = []
        for citation_id in block.citation_refs:
            record = registry.resolve(citation_id)
            if record is None:
                raise RenderError(f"citation_note 引用未注册的 citation: {citation_id}")
            number = registry.footnote_map().get(citation_id)
            label = self._format_citation(record)
            lines.append(f"{number}. {label}" if number is not None else f"- {label}")
        return lines

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

    @staticmethod
    def _assert_no_residue(text: str) -> None:
        if "{{" in text or "}}" in text:
            raise RenderError("Markdown 输出残留模板/引用标记")


def render_markdown(document: DocumentIR, registry: CitationRegistry | None = None) -> str:
    """Convenience entry point: render a DocumentIR to Markdown."""
    return MarkdownRenderer().render(document, registry)


__all__ = ["MarkdownRenderer", "RenderError", "render_markdown"]
