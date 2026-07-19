from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.common.citation.models import CitationItem

_CIT_MARKER_RE = re.compile(r"\{\{(CIT-[A-Z]+-[A-Z0-9]+-(?:ART[A-Z0-9_]+|GEN)-P\d+)\}\}")


@dataclass
class CitationRegistry:
    """Per-report in-memory registry of CitationItems.

    Keyed by citation_id. Built once per report generation and used by the LLM
    marker system, post-processor, and renderer.

    Maintains a global footnote numbering across all chapters so that a given
    citation always receives the same [n] number wherever it appears.
    """

    _items: dict[str, CitationItem] = field(default_factory=dict)
    _global_numbering: dict[str, int] = field(default_factory=dict)
    _next_num: int = 1

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
            if item.display_label:
                label = item.display_label
            else:
                article_hint = f" 第{item.article_no}条" if item.article_no else ""
                label = f"{item.title}{article_hint}"
            lines.append(f"{{{{{cid}}}}} = {label}")
        return "\n".join(lines)

    def assign_footnote_number(self, citation_id: str) -> int | None:
        """Assign (or retrieve) a global footnote number for a citation_id."""
        item = self._items.get(citation_id)
        if item is None:
            return None
        if citation_id not in self._global_numbering:
            self._global_numbering[citation_id] = self._next_num
            self._next_num += 1
        return self._global_numbering[citation_id]

    def get_footnote_map(self) -> dict[int, CitationItem]:
        """Return the global footnote map: {footnote_number: CitationItem}."""
        result: dict[int, CitationItem] = {}
        for cid, num in self._global_numbering.items():
            item = self._items.get(cid)
            if item:
                result[num] = item
        return dict(sorted(result.items()))

    def build_footnote_map(self, text: str) -> dict[int, CitationItem]:
        """Parse {{CIT-xxx}} markers from text, assign footnote numbers by first-appearance order
        within *this text only* (used for legacy per-chapter numbering or standalone use).
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

    def build_citation_map_section(self) -> str:
        """Build a markdown 「引用依据索引」section listing all cited references."""
        footnote_map = self.get_footnote_map()
        if not footnote_map:
            return "（本报告未引用法规依据索引）"

        lines: list[str] = ["## 引用依据索引", ""]
        type_labels: dict[str, str] = {
            "law_article": "法律条文",
            "official_guide": "官方指南",
            "template_requirement": "模板要求",
            "standard_clause": "标准条款",
            "case_reference": "案例参考",
            "user_material": "用户材料",
        }
        for num in sorted(footnote_map):
            item = footnote_map[num]
            type_label = type_labels.get(item.citation_type, item.citation_type)
            article_hint = f" 第{item.article_no}条" if item.article_no else ""
            lines.append(
                f"[{num}] **{item.title}**{article_hint} "
                f"（{type_label}，权威等级：{item.authority_level}）"
            )
            if item.quote_text:
                snippet = item.quote_text[:200].replace("\n", " ")
                lines.append(f"    > {snippet}")
            lines.append("")
        return "\n".join(lines)

    def build_external_citation_map_section(self) -> str:
        """Build citation map section with only external-report-allowed citations.

        Filters by:
        - can_enter_external_report=True (excludes case references)
        - external_report_allowed=True (excludes low-confidence citations)
        """
        footnote_map = self.get_footnote_map()
        if not footnote_map:
            return "（本报告未引用法规依据索引）"

        external_items = {
            num: item
            for num, item in footnote_map.items()
            if item.can_enter_external_report and item.external_report_allowed
        }

        low_confidence_items = {
            num: item
            for num, item in footnote_map.items()
            if item.can_enter_external_report and not item.external_report_allowed
        }

        if not external_items and not low_confidence_items:
            return "（本报告未引用外部可用法规依据索引）"

        type_labels: dict[str, str] = {
            "law_article": "法律条文",
            "official_guide": "官方指南",
            "template_requirement": "模板要求",
            "standard_clause": "标准条款",
            "user_material": "用户材料",
        }
        lines: list[str] = ["## 引用依据索引", ""]

        for num in sorted(external_items):
            item = external_items[num]
            type_label = type_labels.get(item.citation_type, item.citation_type)
            article_hint = f" 第{item.article_no}条" if item.article_no else ""
            lines.append(
                f"[{num}] **{item.title}**{article_hint} "
                f"（{type_label}，权威等级：{item.authority_level}）"
            )
            if item.quote_text:
                snippet = item.quote_text[:200].replace("\n", " ")
                lines.append(f"    > {snippet}")
            lines.append("")

        # Annotate low-confidence citations that were excluded
        if low_confidence_items:
            lines.append("### 引用置信度不足条目（未纳入正式引用索引）")
            lines.append("")
            lines.append("以下法规依据相关性评分低于最低置信阈值，未作为正式引用依据，仅供参考：")
            lines.append("")
            for num in sorted(low_confidence_items):
                item = low_confidence_items[num]
                article_hint = f" 第{item.article_no}条" if item.article_no else ""
                lines.append(
                    f"- **{item.title}**{article_hint} "
                    f"（置信度 {item.confidence_score:.2f} < 阈值 {item.confidence_threshold:.0%}）【待验证】"
                )
            lines.append("")

        return "\n".join(lines)


    def to_list(self) -> list[dict]:
        return [item.to_dict() for item in self._items.values()]
