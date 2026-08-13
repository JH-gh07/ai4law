"""Task067 T08 — reusable layout-contract verifiers.

These functions are *negative checks*: each returns a list of human-readable
diagnostics describing a violation of the issue067 layout contract. An empty
list means the artifact passes. They live here (rather than inline in one test)
so ``test_layout_contract.py``, the mutation tests, and
``scripts/check_report_artifacts.py`` exercise the *same* checks.

The four mutation surfaces called out by the plan are all covered:

- 异常断词 (character-by-character break) → :func:`broken_word_fragments`;
- 表格退化 (six-column detail table) → :func:`six_column_table`;
- Markdown 分隔残留 → :func:`markdown_table_residue`;
- 编号重置 (list numbering restart) → :func:`numbering_sequence_diagnostics`;
- 重复正文 (duplicated body) → :func:`duplicate_body_diagnostics`.
"""

from __future__ import annotations

import re

# The pre-fix six-column grid split short tokens across column rows, so these
# fragments surfaced as *standalone lines* in ``pdftotext`` output — which never
# happens in a correctly flowing paragraph renderer.
BROKEN_TOKEN_FRAGMENTS: tuple[tuple[str, str], ...] = (
    ("HIG", "risk HIGH broken across columns"),
    ("ME", "risk MEDIUM broken across columns"),
    ("DIU", "risk MEDIUM broken across columns"),
    ("-C-1", "finding ID broken character-by-character"),
    (".1", "finding ID broken character-by-character"),
)

# A six-column finding detail table is the source of both the Markdown pipe
# residue and the PDF character break. The new layout uses a short summary
# table plus longitudinal finding blocks instead.
_SIX_COLUMN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\|\s*检查项\s*\|.*\|\s*法律依据\s*\|"),
    re.compile(r"\|\s*主题\s*\|.*\|\s*现状\s*\|.*\|\s*整改建议\s*\|"),
)

_MARKDOWN_SEPARATOR = re.compile(r"\|\s*:?-{2,}:?\s*\|")


def broken_word_fragments(text: str) -> list[str]:
    """Detect column-split token fragments surfaced as standalone lines."""
    standalone = {line.strip() for line in text.splitlines()}
    return [label for fragment, label in BROKEN_TOKEN_FRAGMENTS if fragment in standalone]


def six_column_table(text: str) -> list[str]:
    """Detect the legacy six-column finding detail table."""
    return [
        f"six-column finding table: {pattern.pattern}"
        for pattern in _SIX_COLUMN_PATTERNS
        if pattern.search(text)
    ]


def markdown_table_residue(text: str) -> list[str]:
    """Detect Markdown table-separator residue in a rendered artifact."""
    if "| --- |" in text or _MARKDOWN_SEPARATOR.search(text):
        return ["Markdown table separator residue"]
    return []


def numbering_sequence_diagnostics(text: str, expected_headings: list[str]) -> list[str]:
    """Verify expected clause headings appear in order (no numbering reset).

    A renderer that restarts numbering on a nested list (or loses the level)
    will make a later heading either disappear or reappear out of order, which
    this check flags.
    """
    diagnostics: list[str] = []
    last = -1
    for heading in expected_headings:
        index = text.find(heading)
        if index == -1:
            diagnostics.append(f"clause heading missing: {heading!r}")
        elif index < last:
            diagnostics.append(f"clause numbering reset: {heading!r} at {index} < {last}")
        else:
            last = index
    return diagnostics


def duplicate_body_diagnostics(text: str, unique_anchors: list[str], max_occurrences: int = 1) -> list[str]:
    """Detect a body anchor rendered more times than expected (duplicate body)."""
    diagnostics: list[str] = []
    for anchor in unique_anchors:
        count = text.count(anchor)
        if count > max_occurrences:
            diagnostics.append(f"duplicate body: {anchor!r} rendered {count} times (max {max_occurrences})")
    return diagnostics


__all__ = [
    "BROKEN_TOKEN_FRAGMENTS",
    "broken_word_fragments",
    "duplicate_body_diagnostics",
    "markdown_table_residue",
    "numbering_sequence_diagnostics",
    "six_column_table",
]
