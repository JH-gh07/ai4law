"""Select the bounded legal context sent to PIPIA chapter generation."""

from __future__ import annotations

from dataclasses import dataclass

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry

PIPIA_PROMPT_CITATION_LIMIT = 24

_PIPIA_PRIORITY_CITATIONS = (
    ("CN-LAW-003", "4"),
    ("CN-LAW-003", "5"),
    ("CN-LAW-003", "7"),
    ("CN-LAW-003", "9"),
    ("CN-LAW-003", "13"),
    ("CN-LAW-003", "14"),
    ("CN-LAW-003", "17"),
    ("CN-LAW-003", "21"),
    ("CN-LAW-003", "23"),
    ("CN-LAW-003", "24"),
    ("CN-LAW-003", "28"),
    ("CN-LAW-003", "29"),
    ("CN-LAW-003", "38"),
    ("CN-LAW-003", "39"),
    ("CN-LAW-003", "50"),
    ("CN-LAW-003", "51"),
    ("CN-LAW-003", "52"),
    ("CN-LAW-003", "54"),
    ("CN-LAW-003", "55"),
    ("CN-LAW-003", "57"),
    ("CN-LAW-003", "59"),
    ("CN-REG-004", "5"),
    ("CN-REG-008", "42"),
)


@dataclass(frozen=True)
class PIPIALegalPromptContext:
    citation_ids: list[str]
    citation_labels: list[str]
    marker_section: str
    regulation_snippet: str


def _label(item: CitationItem) -> str:
    if item.display_label:
        return item.display_label
    article = f" 第{item.article_no}条" if item.article_no else ""
    return f"{item.title}{article}".strip()


def build_pipia_legal_prompt_context(
    registry: CitationRegistry,
) -> PIPIALegalPromptContext:
    """Keep the report registry intact while bounding the model-facing subset."""
    items = list(registry)
    by_key = {(item.source_id, str(item.article_no or "")): item for item in items}
    selected: list[CitationItem] = []
    selected_ids: set[str] = set()

    for key in _PIPIA_PRIORITY_CITATIONS:
        item = by_key.get(key)
        if item is not None and item.citation_id not in selected_ids:
            selected.append(item)
            selected_ids.add(item.citation_id)
        if len(selected) >= PIPIA_PROMPT_CITATION_LIMIT:
            break

    for item in items:
        if len(selected) >= PIPIA_PROMPT_CITATION_LIMIT:
            break
        if item.citation_id not in selected_ids:
            selected.append(item)
            selected_ids.add(item.citation_id)

    labels = [_label(item) for item in selected]
    marker_section = "\n".join(
        f"{{{{{item.citation_id}}}}} = {label}"
        for item, label in zip(selected, labels, strict=True)
    ) or "（暂无可用引用依据）"
    regulation_snippet = "\n".join(
        f"- {label}：{(item.quote_text or '')[:160]}"
        for item, label in zip(selected, labels, strict=True)
    ) or "（暂无检索到相关法条）"

    return PIPIALegalPromptContext(
        citation_ids=[item.citation_id for item in selected],
        citation_labels=labels,
        marker_section=marker_section,
        regulation_snippet=regulation_snippet,
    )
