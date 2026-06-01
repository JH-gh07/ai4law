from __future__ import annotations

LAW_ABBREVIATIONS: dict[str, str] = {
    "PIPL": "个人信息保护法",
    "DSL": "数据安全法",
    "CSL": "网络安全法",
    "EXPORT-ASSESSMENT": "数据出境安全评估办法",
    "SCC": "个人信息出境标准合同办法",
    "CERTIFICATION": "个人信息保护认证实施规则",
    "EXPORT-GUIDE": "数据出境安全评估申报指南",
    "DATA-CLASSIFICATION": "数据分类分级管理办法",
    "IMPORTANT-DATA": "重要数据识别指南",
    "MULTI-LEVEL": "网络安全等级保护条例",
}

# Reverse lookup: full title → abbreviation
TITLE_TO_ABBR: dict[str, str] = {v: k for k, v in LAW_ABBREVIATIONS.items()}


def _normalize_title(title: str) -> str:
    return title.replace("《", "").replace("》", "").strip()


def resolve_abbreviation(title: str) -> str:
    """Map a full regulation title to its abbreviation, falling back to a short acronym."""
    key = _normalize_title(title)
    if key in TITLE_TO_ABBR:
        return TITLE_TO_ABBR[key]
    # fuzzy: check substring match
    for full_title, abbr in TITLE_TO_ABBR.items():
        if key in full_title or full_title in key:
            return abbr
    # fallback: first 3 uppercase chars from title
    chars = "".join(ch for ch in key if ch.isascii() and ch.isupper())
    if len(chars) >= 2:
        return chars[:8].upper()
    return "UNKNOWN"


def generate_citation_id(jurisdiction: str, abbr: str, article_no: str, seq: int = 1) -> str:
    """Generate a unique citation ID.

    Example: generate_citation_id("CN", "PIPL", "39", 1) → "CIT-CN-PIPL-ART39-P01"
    """
    article_part = f"ART{article_no}" if article_no else "GEN"
    return f"CIT-{jurisdiction.upper()}-{abbr.upper()}-{article_part}-P{seq:02d}"
