from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES_CSV = ROOT / "doc/knowledge/index/sources.csv"
CASES_CSV = ROOT / "doc/knowledge/index/practice_cases.csv"
REGISTRY_DIR = ROOT / "doc/knowledge/registry"
MODULE_CATALOG = REGISTRY_DIR / "module_catalog.v1.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except FileNotFoundError:
        return ""


def get_knowledge_sync_meta(*, cache_refreshed: bool) -> dict[str, object]:
    return {
        "synced_at": _now_iso(),
        "cache_refreshed": cache_refreshed,
        "sources_csv_path": str(SOURCES_CSV),
        "cases_csv_path": str(CASES_CSV),
        "module_catalog_path": str(MODULE_CATALOG),
        "sources_csv_exists": SOURCES_CSV.exists(),
        "cases_csv_exists": CASES_CSV.exists(),
        "module_catalog_exists": MODULE_CATALOG.exists(),
        "sources_csv_mtime": _mtime_iso(SOURCES_CSV),
        "cases_csv_mtime": _mtime_iso(CASES_CSV),
        "module_catalog_mtime": _mtime_iso(MODULE_CATALOG),
    }


def refresh_knowledge_cache() -> None:
    _load_sources_index.cache_clear()
    _load_practice_cases.cache_clear()


def load_sources_index() -> list[dict[str, str]]:
    return list(_load_sources_index())


def load_practice_cases() -> list[dict[str, str]]:
    return list(_load_practice_cases())


@lru_cache(maxsize=1)
def _load_sources_index() -> tuple[dict[str, str], ...]:
    if not SOURCES_CSV.exists():
        return ()
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as fp:
        return tuple({k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fp))


@lru_cache(maxsize=1)
def _load_practice_cases() -> tuple[dict[str, str], ...]:
    if not CASES_CSV.exists():
        return ()
    with CASES_CSV.open("r", encoding="utf-8", newline="") as fp:
        return tuple({k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fp))


def read_text_preview(snapshot_path: str, *, limit: int = 600) -> str:
    raw = (snapshot_path or "").strip()
    if not raw:
        return ""
    path = Path(raw)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""
    return (text[: max(0, limit)]).replace("\r\n", "\n").replace("\r", "\n")


def resolve_citation(query: str, *, sources: list[dict[str, str]]) -> dict[str, str] | None:
    """Best-effort citation resolver for the Knowledge Center UI.

    This endpoint is primarily for mapping a free-form citation string back to a row
    in `sources.csv`. It intentionally stays lightweight and local.
    """
    text = (query or "").strip()
    if not text:
        return None

    lowered = text.lower()
    for row in sources:
        source_id = (row.get("source_id") or "").strip()
        title = (row.get("title") or "").strip()
        if source_id and source_id.lower() in lowered:
            return row
        if title and title.lower() in lowered:
            return row
    return None


def get_article_detail(source_id: str, article_no: str) -> dict | None:
    """Retrieve a specific article from the knowledge base by source_id and article_no.

    Looks up the source in sources.csv for metadata, then reads the article text
    from the raw snapshot file. Returns the target article with context (prev/next).
    """
    sources = list(_load_sources_index())
    source = None
    for row in sources:
        if (row.get("source_id") or "").strip() == source_id:
            source = row
            break
    if source is None:
        return None

    snapshot_path = (source.get("snapshot_path") or "").strip()
    if not snapshot_path:
        return None

    path = Path(snapshot_path)
    if not path.is_absolute():
        path = (ROOT / path).resolve()

    try:
        full_text = path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return None

    full_text = full_text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip HTML tags for clean text parsing
    full_text = re.sub(r'<[^>]+>', '', full_text)

    # Extract articles from the full text using structural markers
    articles = _parse_articles_from_text(full_text)

    target = articles.get(article_no)
    if not target:
        return None

    # Find prev/next article numbers
    sorted_nums = sorted(articles.keys(), key=lambda x: _article_sort_key(x))
    idx = sorted_nums.index(article_no) if article_no in sorted_nums else -1
    prev_no = sorted_nums[idx - 1] if idx > 0 else None
    next_no = sorted_nums[idx + 1] if idx >= 0 and idx < len(sorted_nums) - 1 else None

    return {
        "source_id": source_id,
        "title": (source.get("title") or "").strip(),
        "article_no": article_no,
        "article_content": target,
        "prev_article_no": prev_no,
        "prev_article_content": articles.get(prev_no, "") if prev_no else "",
        "next_article_no": next_no,
        "next_article_content": articles.get(next_no, "") if next_no else "",
        "source_url": (source.get("url") or "").strip(),
        "authority_level": (source.get("authority_level") or "medium").strip(),
        "binding_force": (source.get("binding_force") or "recommended").strip(),
        "jurisdiction": (source.get("jurisdiction") or "cn").strip(),
        "doc_type": (source.get("doc_type") or "law").strip(),
    }


def _article_sort_key(num_str: str) -> int:
    """Sort article numbers numerically; Chinese numerals yield high values."""
    try:
        return int(num_str)
    except ValueError:
        return 99999


def _parse_articles_from_text(full_text: str) -> dict[str, str]:
    """Parse a Chinese law text into a dict of {article_no: article_text}.

    Uses a two-pass approach: first find all article header positions, then
    split the text at those boundaries. This avoids the common pitfall of
    content regexes consuming subsequent article markers.
    """
    # Match article headers: 第X条 with optional suffix (之一/之二/之三)
    header_re = re.compile(
        r'第([一二三四五六七八九十百千零\d]+)条(?:之一|之二|之三)?'
    )

    # Find all header positions and article numbers
    headers: list[tuple[int, int, str]] = []  # (start, end, article_no)
    for m in header_re.finditer(full_text):
        raw_num = m.group(1)
        try:
            num = str(_chinese_to_int(raw_num))
        except ValueError:
            num = raw_num
        # Only record if this looks like a structural header
        # In HTML files, headers may be inside tags (e.g. <strong>第三条</strong>),
        # so we check that the char before 第 is a non-alphanumeric boundary character
        start = m.start()
        if start == 0 or not full_text[start - 1].isalnum():
            headers.append((start, m.end(), num))

    if not headers:
        return {}

    result: dict[str, str] = {}
    for i, (hdr_start, hdr_end, num) in enumerate(headers):
        # Content starts after header, ends at next header (or end of text)
        content_start = hdr_end
        content_end = headers[i + 1][0] if i + 1 < len(headers) else len(full_text)
        content = full_text[content_start:content_end].strip()
        result[num] = content

    return result


def _chinese_to_int(chinese: str) -> int:
    """Convert Chinese numeral to integer (simplified: handles 一 to 九百九十九)."""
    if chinese.isdigit():
        return int(chinese)

    chinese_numerals = {
        "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100,
        "千": 1000, "万": 10000,
    }

    total = 0
    current = 0
    for char in chinese:
        if char in ("十", "百", "千", "万"):
            if current == 0:
                current = 1
            total += current * chinese_numerals[char]
            current = 0
        elif char in chinese_numerals:
            current = chinese_numerals[char]
    total += current
    return total
