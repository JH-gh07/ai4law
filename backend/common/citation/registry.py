from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.common.citation.models import CitationItem

_CIT_MARKER_RE = re.compile(r"\{\{(CIT-[A-Z]+-[A-Z0-9]+-ART\d+-P\d+)\}\}")


@dataclass
class CitationRegistry:
    """Per-report in-memory registry of CitationItems.

    Keyed by citation_id. Built once per report generation and used by the LLM
    marker system, post-processor, and renderer.
    """

    _items: dict[str, CitationItem] = field(default_factory=dict)

    def register(self, item: CitationItem) -> str:
        self._items[item.citation_id] = item
        return item.citation_id

    def get(self, citation_id: str) -> CitationItem | None:
        return self._items.get(citation_id)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items.values())

    def build_marker_list(self) -> str:
        """Generate the 「可引用法规依据」table for the LLM prompt."""
        if not self._items:
            return "（暂无可用引用依据）"
        lines: list[str] = []
        for cid, item in self._items.items():
            article_hint = f" 第{item.article_no}条" if item.article_no else ""
            lines.append(f"{{{{{cid}}}}} = {item.title}{article_hint}")
        return "\n".join(lines)

    def build_footnote_map(self, text: str) -> dict[int, CitationItem]:
        """Parse {{CIT-xxx}} markers from text, assign footnote numbers by first-appearance order.

        Returns dict mapping footnote number (int) → CitationItem.
        Markers not found in the registry are silently skipped.
        """
        markers = _CIT_MARKER_RE.findall(text)
        seen: dict[str, int] = {}
        result: dict[int, CitationItem] = {}
        next_num = 1
        for marker in markers:
            if marker in seen:
                continue
            item = self._items.get(marker)
            if item is None:
                continue
            seen[marker] = next_num
            result[next_num] = item
            next_num += 1
        return result

    def to_list(self) -> list[dict]:
        return [item.to_dict() for item in self._items.values()]
