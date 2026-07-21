"""Render the shared report model as Markdown."""

from __future__ import annotations

from pathlib import Path

from backend.common.llm.postprocess import normalize_legal_markdown_structure
from backend.common.render.report_model import (
    DividerBlock,
    HeadingBlock,
    ListBlock,
    Paragraph,
    ReportDocument,
    TableBlock,
)


class MarkdownRenderer:
    def render(self, document: ReportDocument) -> str:
        meta = document.metadata
        lines = [f"# {meta.title}"]
        if meta.company_name:
            lines.append(f"**企业**: {meta.company_name}")
        if meta.report_date:
            lines.append(f"**日期**: {meta.report_date}")
        lines.append("")

        for section in document.sections:
            lines.extend([f"{'#' * min(max(section.level, 1), 6)} {section.heading}", ""])
            for block in section.blocks:
                lines.extend(self._block(block))
                lines.append("")
        return normalize_legal_markdown_structure("\n".join(lines))

    def render_to_file(self, document: ReportDocument, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(document), encoding="utf-8")
        return output_path

    def _block(self, block) -> list[str]:
        if isinstance(block, Paragraph):
            return [block.text.strip()] if block.text.strip() else []
        if isinstance(block, HeadingBlock):
            return [f"{'#' * min(max(block.level, 1), 6)} {block.text}"]
        if isinstance(block, ListBlock):
            prefix = "1. " if block.ordered else "- "
            return [f"{prefix}{item}" for item in block.items]
        if isinstance(block, TableBlock):
            return self._table(block)
        if isinstance(block, DividerBlock):
            return ["---"]
        raise TypeError(f"Unsupported report block: {type(block).__name__}")

    @staticmethod
    def _table(table: TableBlock) -> list[str]:
        if not table.headers:
            return []
        escape_cell = lambda value: str(value).replace("|", "\\|").replace("\n", " ").strip()
        lines = [
            "| " + " | ".join(escape_cell(item) for item in table.headers) + " |",
            "| " + " | ".join("---" for _ in table.headers) + " |",
        ]
        for row in table.rows:
            cells = [escape_cell(item) for item in row[: len(table.headers)]]
            cells.extend([""] * (len(table.headers) - len(cells)))
            lines.append("| " + " | ".join(cells) + " |")
        return lines
