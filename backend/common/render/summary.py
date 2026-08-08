from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.common.llm.postprocess import apply_citation_policy

if TYPE_CHECKING:
    from backend.common.citation.registry import CitationRegistry


_HEADING_PATTERNS = (
    re.compile(r"^\s{0,3}#{1,6}\s+"),
    re.compile(r"^\s{0,3}（?[一二三四五六七八九十]+[、.）)]\s*"),
    re.compile(r"^\s{0,3}[0-9]+[、.）)]\s*"),
)


def summarize_for_slot(
    text: str,
    max_sentences: int = 3,
    max_chars: int = 320,
) -> str:
    """Condense long section text into a short, slot-friendly summary.

    - Removes heading markers and list item labels.
    - Keeps first N sentences.
    - Truncates to max_chars with ellipsis.
    """
    if not text:
        return "未提供"

    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # drop pure headings
        dropped = False
        for pattern in _HEADING_PATTERNS:
            if pattern.match(line):
                line = pattern.sub("", line).strip()
                if not line:
                    dropped = True
                break
        if dropped:
            continue
        # remove leading bullets
        line = re.sub(r"^\s*[-*•]\s*", "", line)
        if line:
            lines.append(line)

    if not lines:
        return "未提供"

    text = " ".join(lines)
    # split by Chinese/English sentence enders
    parts = re.split(r"(?<=[。！？.!?])\s*", text)
    parts = [p.strip() for p in parts if p.strip()]
    if parts:
        text = " ".join(parts[:max_sentences])

    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"

    return text


def dedup_if_same(primary: str, secondary: str, fallback: str) -> tuple[str, str]:
    """If primary and secondary are essentially identical, replace primary with fallback."""
    def norm(value: str) -> str:
        return re.sub(r"\s+", "", (value or "")).lower()

    if primary and secondary and norm(primary) == norm(secondary):
        return fallback, secondary
    return primary, secondary


def attach_citations(
    text: str,
    citations: list[str] | None,
    max_items: int = 3,
    *,
    registry: "CitationRegistry | None" = None,
) -> str:
    """Apply the citation gate, using the shared registry when available.

    Calls without a registry remain a compatibility path for legacy callers;
    production report paths must pass the report's registry.
    """
    if not text or text == "未提供":
        return text
    if registry is not None:
        from backend.common.llm.postprocess import apply_citation_pipeline

        basis = "；".join(str(item).strip() for item in (citations or []) if str(item).strip())
        marked = f"{text.rstrip()}【依据：{basis}】" if basis and "【依据：" not in text else text
        return apply_citation_pipeline(
            marked,
            registry=registry,
            allowed_citations=citations,
            max_items=max_items,
        ).text
    return apply_citation_policy(text, citations, max_items=max_items).text
