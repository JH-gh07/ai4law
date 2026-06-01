"""Chinese legal document structure patterns.

Regex patterns for detecting structural boundaries in Chinese legal texts
according to the standard hierarchy: chapter (章) → section (节) → article (条)
→ paragraph (款) → item (项).
"""

import re

# Article marker: "第X条" where X can be Chinese numeral or Arabic digits
ARTICLE_PATTERN = re.compile(
    r"^\s*第[一二三四五六七八九十百千\d]+条\b"
)

# Chapter marker: "第X章"
CHAPTER_PATTERN = re.compile(
    r"^\s*第[一二三四五六七八九十百千\d]+章\b"
)

# Section marker: "第X节"
SECTION_PATTERN = re.compile(
    r"^\s*第[一二三四五六七八九十百千\d]+节\b"
)

# Paragraph marker: "第X款"
PARAGRAPH_PATTERN = re.compile(
    r"^\s*第[一二三四五六七八九十百千\d]+款\b"
)

# Item marker: "（一）" or "(一)" or "（1）"
ITEM_PATTERN = re.compile(
    r"^\s*[（(][一二三四五六七八九十\d]+[)）]"
)

# Generic numbered list: "一、" or "1、" or "(1)"
GENERIC_LIST_PATTERN = re.compile(
    r"^\s*(?:[一二三四五六七八九十]+、|\d+[.、]|[（(]\d+[)）])"
)

# Law title pattern: "《...法》" or "《...办法》" etc.
LAW_TITLE_PATTERN = re.compile(
    r"《[^》]+》"
)

# Structural level ordering (for sorting)
LEVEL_ORDER: dict[str, int] = {
    "chapter": 0,
    "section": 1,
    "article": 2,
    "paragraph": 3,
    "item": 4,
    "text": 5,
}


def detect_structure(line: str) -> tuple[str | None, str | None]:
    """Detect the structural level and label from a line of Chinese legal text.

    Returns (level, label) where level is one of:
    'chapter', 'section', 'article', 'paragraph', 'item', 'text', or None.

    Label is the extracted reference like "第一章" or "第三十九条" or None.
    """
    stripped = line.strip()
    if not stripped:
        return None, None

    if CHAPTER_PATTERN.match(stripped):
        return "chapter", stripped.split(maxsplit=1)[0] if " " in stripped else stripped

    if SECTION_PATTERN.match(stripped):
        return "section", stripped.split(maxsplit=1)[0] if " " in stripped else stripped

    if ARTICLE_PATTERN.match(stripped):
        return "article", stripped.split(maxsplit=1)[0] if " " in stripped else stripped

    if PARAGRAPH_PATTERN.match(stripped):
        return "paragraph", stripped.split(maxsplit=1)[0] if " " in stripped else stripped

    if ITEM_PATTERN.match(stripped):
        return "item", stripped.split(maxsplit=1)[0] if " " in stripped else stripped

    return None, None


def extract_title_from_text(text: str, max_lines: int = 10) -> str | None:
    """Try to extract a law title from the beginning of a document."""
    lines = text.strip().split("\n")[:max_lines]
    for line in lines:
        match = LAW_TITLE_PATTERN.search(line)
        if match:
            return match.group(0).replace("《", "").replace("》", "")
    # fallback: first non-empty line
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) >= 4:
            return stripped[:120]
    return None
