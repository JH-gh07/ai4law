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

    Footnote numbers are assigned by first-appearance order within the text.
    """
    if not text:
        return text

    # Build footnote map to determine numbering
    footnote_map = registry.build_footnote_map(text)
    if not footnote_map:
        return text

    # Create reverse lookup: citation_id → footnote_number
    cid_to_num: dict[str, int] = {}
    for num, item in footnote_map.items():
        cid_to_num[item.citation_id] = num

    def _replace_marker(match: re.Match) -> str:
        cid = match.group(1)
        num = cid_to_num.get(cid)
        if num is not None:
            return f"[{num}]"
        return ""

    return _CIT_MARKER_RE.sub(_replace_marker, text)

