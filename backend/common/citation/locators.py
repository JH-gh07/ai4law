from __future__ import annotations

import re


_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}
_ARTICLE_PATTERN = re.compile(
    r"第\s*([0-9]+|[零〇一二两三四五六七八九十百千万]+)\s*条"
    r"(?:之\s*([0-9]+|[零〇一二两三四五六七八九十百千万]+))?"
)


def normalize_article_no(article_no: str) -> str:
    """Return one canonical locator for URLs, registry counts, and detail lookup."""
    value = (article_no or "").strip()
    if not value:
        return ""

    match = _ARTICLE_PATTERN.search(value)
    if match:
        base = _normalize_numeral(match.group(1))
        suffix = _normalize_numeral(match.group(2)) if match.group(2) else ""
        return f"{base}之{suffix}" if suffix else base

    if "之" in value:
        base, suffix = value.split("之", 1)
        normalized_base = _normalize_numeral(base)
        normalized_suffix = _normalize_numeral(suffix)
        if normalized_base and normalized_suffix:
            return f"{normalized_base}之{normalized_suffix}"

    return _normalize_numeral(value)


def _normalize_numeral(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if raw.isdigit():
        return str(int(raw))
    if any(char not in _DIGITS and char not in _UNITS for char in raw):
        return raw

    total = 0
    section = 0
    number = 0
    for char in raw:
        if char in _DIGITS:
            number = _DIGITS[char]
            continue
        unit = _UNITS[char]
        if unit == 10000:
            section = (section + number) * unit
            total += section
            section = 0
        else:
            section += (number or 1) * unit
        number = 0
    result = total + section + number
    return str(result) if result > 0 else raw
