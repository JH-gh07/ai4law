from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.citation.registry import CitationRegistry

_CIT_MARKER_RE = re.compile(r"\{\{(CIT-[A-Z]+-[A-Z0-9]+-ART\d+-P\d+)\}\}")


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
    return "\n\n".join(rendered)


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

    return _CIT_MARKER_RE.sub(_replace_marker, text)

