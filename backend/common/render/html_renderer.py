"""Render the shared report model as escaped, self-contained HTML."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

from backend.common.render.report_model import (
    DividerBlock,
    HeadingBlock,
    ListBlock,
    Paragraph,
    ReportDocument,
    TableBlock,
)


class HtmlRenderer:
    _CSS = (
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "max-width:960px;margin:28px auto;padding:0 16px;line-height:1.6;color:#1f2937}"
        "table{width:100%;border-collapse:collapse;margin:10px 0}"
        "th,td{border:1px solid #d0d7de;padding:6px 8px;text-align:left}"
        "th{background:#eef5ff}ul,ol{padding-left:20px}"
    )

    def render(self, document: ReportDocument) -> str:
        meta = document.metadata
        parts = [
            "<!doctype html>",
            '<html lang="zh-CN">',
            '<head><meta charset="utf-8" />',
            f"<title>{escape(meta.title)}</title><style>{self._CSS}</style></head>",
            "<body>",
            f"<h1>{escape(meta.title)}</h1>",
        ]
        if meta.company_name:
            parts.append(
                f'<p class="meta">企业: {escape(meta.company_name)} | '
                f"日期: {escape(meta.report_date)}</p>"
            )
        for section in document.sections:
            level = min(max(section.level, 1), 6)
            parts.append(f"<h{level}>{escape(section.heading)}</h{level}>")
            parts.extend(self._block(block) for block in section.blocks)
        parts.extend(["</body>", "</html>"])
        return "\n".join(parts)

    def render_to_file(self, document: ReportDocument, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(document), encoding="utf-8")
        return output_path

    def _block(self, block) -> str:
        if isinstance(block, Paragraph):
            return f"<p>{self._inline(block.text)}</p>"
        if isinstance(block, HeadingBlock):
            level = min(max(block.level, 1), 6)
            return f"<h{level}>{self._inline(block.text)}</h{level}>"
        if isinstance(block, ListBlock):
            tag = "ol" if block.ordered else "ul"
            items = "".join(f"<li>{self._inline(item)}</li>" for item in block.items)
            return f"<{tag}>{items}</{tag}>"
        if isinstance(block, TableBlock):
            headers = "".join(f"<th>{self._inline(item)}</th>" for item in block.headers)
            rows = "".join(
                "<tr>"
                + "".join(
                    f"<td>{self._inline(cell)}</td>" for cell in row[: len(block.headers)]
                )
                + "</tr>"
                for row in block.rows
            )
            return f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"
        if isinstance(block, DividerBlock):
            return "<hr />"
        raise TypeError(f"Unsupported report block: {type(block).__name__}")

    @staticmethod
    def _inline(text: str) -> str:
        safe = escape(text or "")
        safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
