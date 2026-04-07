from __future__ import annotations

import re


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


def attach_citations(text: str, citations: list[str] | None, max_items: int = 3) -> str:
    if not text or text == "未提供":
        return text
    if "【依据：" in text:
        return text
    items = [str(c).strip() for c in (citations or []) if str(c).strip()]
    if items:
        basis = "；".join(items[:max_items])
    else:
        basis = "未检索到"
    separator = " " if text and not text.endswith(" ") else ""
    return f"{text}{separator}【依据：{basis}】"
