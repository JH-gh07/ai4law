from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.citation.registry import CitationRegistry

_CIT_MARKER_RE = re.compile(r"\{\{(CIT-[A-Z]+-[A-Z0-9]+-ART\d+-P\d+)\}\}")
_CHAPTER_LABEL_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇两0-9]+章\b")
_SECTION_LABEL_RE = re.compile(r"^[一二三四五六七八九十百千万零〇两0-9]+、")
_SUBSECTION_LABEL_RE = re.compile(r"^（[一二三四五六七八九十百千万零〇两0-9]+）")
_ORDERED_ITEM_RE = re.compile(r"^(?:\(?(\d+)\)|(\d+)[、.])\s*")
_MARKDOWN_PREFIX_RE = re.compile(r"^\s*(?:#{1,6}\s|[-*]\s|\d+\.\s|>\s|\|)")
_BASIS_BLOCK_RE = re.compile(r"【依据：[^】]+】")


def normalize_legal_markdown_structure(text: str) -> str:
    """Normalize loosely structured legal prose into stable Markdown blocks.

    Goals:
    - split packed headings like "第一章...一、...（一）..."
    - keep existing Markdown headings/lists/tables intact
    - force legal basis blocks onto their own lines
    - render Chinese legal document hierarchy into Markdown headings
    """
    if not text:
        return text

    normalized = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u00a0", " ")
        .replace("\u3000", " ")
    )
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)

    items: list[tuple[str, str]] = []
    for raw_line in normalized.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue
        for segment in _explode_packed_line(stripped):
            kind, rendered = _classify_legal_block(segment)
            if rendered:
                items.append((kind, rendered))

    if not items:
        return ""

    rendered_parts: list[str] = []
    prev_kind: str | None = None
    for kind, value in items:
        if rendered_parts:
            separator = "\n\n"
            if kind in {"list_item", "table_row"} and prev_kind == kind:
                separator = "\n"
            elif kind == "table_row" and prev_kind == "table_rule":
                separator = "\n"
            elif kind == "table_rule" and prev_kind == "table_row":
                separator = "\n"
            elif kind == "table_rule" and prev_kind == "table_rule":
                separator = "\n"
            rendered_parts.append(separator)
        rendered_parts.append(value)
        prev_kind = kind

    output = "".join(rendered_parts)
    output = re.sub(r"\n{3,}", "\n\n", output)
    return output.strip()


def _explode_packed_line(line: str) -> list[str]:
    line = re.sub(r"\s*(【依据：[^】]+】)", r"\n\1", line)

    if not _MARKDOWN_PREFIX_RE.match(line):
        line = re.sub(r"(?<!\n)(第[一二三四五六七八九十百千万零〇两0-9]+章)", r"\n\1", line)
        line = re.sub(r"(?<!\n)([一二三四五六七八九十百千万零〇两0-9]+、)", r"\n\1", line)
        line = re.sub(r"(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)", r"\n\1", line)
        line = re.sub(r"(?<!\n)(\(?\d+\)|\d+[、.])\s*(?=\S)", lambda m: f"\n{m.group(1)} ", line)

    return [part.strip() for part in line.split("\n") if part.strip()]


def _classify_legal_block(line: str) -> tuple[str, str]:
    if _BASIS_BLOCK_RE.fullmatch(line):
        return "basis", line

    if line.startswith("|"):
        if re.fullmatch(r"\|?[\s:|-]+\|?", line):
            return "table_rule", line
        return "table_row", line

    if _MARKDOWN_PREFIX_RE.match(line):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            return "heading", line
        if stripped.startswith("|"):
            if re.fullmatch(r"\|?[\s:|-]+\|?", stripped):
                return "table_rule", line
            return "table_row", line
        if re.match(r"^\d+\.\s", stripped) or re.match(r"^[-*]\s", stripped):
            return "list_item", line
        return "paragraph", line

    if _CHAPTER_LABEL_RE.match(line):
        return "heading", f"# {line}"
    if _SECTION_LABEL_RE.match(line):
        return "heading", f"## {line}"
    if _SUBSECTION_LABEL_RE.match(line):
        return "heading", f"### {line}"

    ordered = _ORDERED_ITEM_RE.match(line)
    if ordered:
        number = ordered.group(1) or ordered.group(2) or "1"
        rest = line[ordered.end():].strip()
        return "list_item", f"{number}. {rest}".rstrip()

    return "paragraph", line


def ensure_paragraph_citations(
    text: str,
    citations: list[str] | None,
    max_items: int = 3,
) -> str:
    if not text:
        return text
    items = [str(c).strip() for c in (citations or []) if str(c).strip()]
    basis = "；".join(items[:max_items]) if items else "未检索到"

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    rendered: list[str] = []
    for paragraph in paragraphs:
        if "【依据：" in paragraph:
            rendered.append(paragraph)
            continue
        rendered.append(f"{paragraph} 【依据：{basis}】")
    return normalize_legal_markdown_structure("\n\n".join(rendered))


def convert_citation_markers(text: str, registry: "CitationRegistry") -> str:
    """Convert {{CIT-xxx}} markers to [1], [2] footnotes in text.

    Uses global footnote numbering from the registry so a citation always
    receives the same number across all chapters.
    """
    if not text:
        return text

    def _replace_marker(match: re.Match) -> str:
        cid = match.group(1)
        num = registry.assign_footnote_number(cid)
        if num is not None:
            return f"[{num}]"
        return ""

    return normalize_legal_markdown_structure(_CIT_MARKER_RE.sub(_replace_marker, text))
