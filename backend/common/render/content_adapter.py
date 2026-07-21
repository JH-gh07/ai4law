"""Adapters from existing chapter data to the shared report model."""

from __future__ import annotations

import re

from backend.common.render.report_model import (
    DividerBlock,
    HeadingBlock,
    ListBlock,
    Paragraph,
    ReportDocument,
    ReportMetadata,
    TableBlock,
)

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_UNORDERED = re.compile(r"^[-*+]\s+(.+)$")
_ORDERED = re.compile(r"^\d+[.)、]\s*(.+)$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?(?:\s*\|\s*:?-{3,}:?)+\s*\|?\s*$")


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_markdown_blocks(content: str) -> list:
    lines = (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(Paragraph("\n".join(paragraph).strip()))
            paragraph.clear()

    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            flush_paragraph()
            index += 1
            continue

        heading = _HEADING.match(stripped)
        if heading:
            flush_paragraph()
            blocks.append(HeadingBlock(heading.group(2), len(heading.group(1))))
            index += 1
            continue
        if stripped == "---":
            flush_paragraph()
            blocks.append(DividerBlock())
            index += 1
            continue

        list_match = _UNORDERED.match(stripped) or _ORDERED.match(stripped)
        if list_match:
            flush_paragraph()
            ordered = _ORDERED.match(stripped) is not None
            pattern = _ORDERED if ordered else _UNORDERED
            items: list[str] = []
            while index < len(lines):
                match = pattern.match(lines[index].strip())
                if not match:
                    break
                items.append(match.group(1).strip())
                index += 1
            blocks.append(ListBlock(items, ordered))
            continue

        if (
            "|" in stripped
            and index + 1 < len(lines)
            and _TABLE_SEPARATOR.match(lines[index + 1].strip())
        ):
            flush_paragraph()
            headers = _table_cells(stripped)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(_table_cells(lines[index]))
                index += 1
            blocks.append(TableBlock(headers, rows))
            continue

        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    return blocks


class ContentAdapter:
    @staticmethod
    def from_chapters(
        title: str,
        company_name: str = "",
        chapters: list[dict] | None = None,
        *,
        module: str = "",
        jurisdiction: str = "cn",
    ) -> ReportDocument:
        document = ReportDocument(
            ReportMetadata(
                title=title,
                company_name=company_name,
                module=module,
                jurisdiction=jurisdiction,
            )
        )
        for chapter in chapters or []:
            section = document.add_section(str(chapter.get("title", "")), level=2)
            section.blocks.extend(parse_markdown_blocks(str(chapter.get("content", ""))))
        return document

    @staticmethod
    def from_sections_list(
        title: str,
        company_name: str = "",
        sections: list[tuple[str, str]] | None = None,
        *,
        module: str = "",
    ) -> ReportDocument:
        return ContentAdapter.from_chapters(
            title,
            company_name,
            [{"title": heading, "content": content} for heading, content in sections or []],
            module=module,
        )

    @staticmethod
    def from_diagnosis(
        company_name: str, sections: list[tuple[str, str]] | None = None
    ) -> ReportDocument:
        return ContentAdapter.from_sections_list(
            f"{company_name} 合规路径诊断报告",
            company_name,
            sections,
            module="diagnosis",
        )

    @staticmethod
    def from_review_sections(
        title: str,
        sections: list[tuple[str, list[str]]] | None = None,
        *,
        company_name: str = "",
    ) -> ReportDocument:
        document = ReportDocument(
            ReportMetadata(title=title, company_name=company_name, module="review")
        )
        for heading, paragraphs in sections or []:
            section = document.add_section(heading)
            section.blocks.extend(Paragraph(text.strip()) for text in paragraphs if text.strip())
        return document
