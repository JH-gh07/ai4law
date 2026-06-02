from __future__ import annotations

import csv
import html
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
    preview = _build_preview_text(text)
    return preview[: max(0, limit)]


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

    full_text = _clean_source_text(full_text)

    # Extract articles from the full text using structural markers
    articles = _parse_articles_from_text(full_text)

    requested_article_no = _normalize_article_lookup_key(article_no)
    target = articles.get(requested_article_no)
    if not target:
        return None

    # Find prev/next article numbers
    sorted_nums = sorted(articles.keys(), key=lambda x: _article_sort_key(x))
    idx = sorted_nums.index(requested_article_no) if requested_article_no in sorted_nums else -1
    prev_no = sorted_nums[idx - 1] if idx > 0 else None
    next_no = sorted_nums[idx + 1] if idx >= 0 and idx < len(sorted_nums) - 1 else None

    return {
        "source_id": source_id,
        "title": (source.get("title") or "").strip(),
        "article_no": requested_article_no,
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


def _normalize_article_lookup_key(article_no: str) -> str:
    value = (article_no or "").strip()
    if not value:
        return value
    if value.isdigit():
        return value
    match = re.search(r"第([一二三四五六七八九十百千零\d]+)条", value)
    if match:
        raw_num = match.group(1)
        try:
            return str(_chinese_to_int(raw_num))
        except ValueError:
            return raw_num
    try:
        return str(_chinese_to_int(value))
    except ValueError:
        return value


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


def _clean_source_text(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if "<" in normalized and ">" in normalized:
        normalized = _extract_text_from_html(_extract_primary_html_segment(normalized))
    normalized = html.unescape(normalized)
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _build_preview_text(text: str) -> str:
    cleaned = _clean_source_text(text)
    if not cleaned:
        return ""
    lines = [_normalize_preview_line(line) for line in cleaned.splitlines()]
    filtered = [line for line in lines if line and not _is_preview_noise(line)]
    if not filtered:
        return ""

    start = _select_preview_start(filtered)
    kept: list[str] = []
    for line in filtered[start:]:
        if _is_preview_footer(line):
            break
        kept.append(line)
        if len(kept) >= 8 or sum(len(item) for item in kept) >= 1200:
            break
    return "\n\n".join(kept[:8]).strip()


def _extract_primary_html_segment(html_text: str) -> str:
    lowered = html_text.lower()
    markers = [
        "trs_editor_view",
        "trs_ueditor",
        "article-content",
        "articlebody",
        "content-main",
        "details-body",
        "detail-content",
        "<article",
        "<main",
    ]
    for marker in markers:
        idx = lowered.find(marker)
        if idx >= 0:
            start = max(0, idx - 400)
            end = min(len(html_text), idx + 50000)
            return html_text[start:end]
    return html_text


def _extract_text_from_html(html_text: str) -> str:
    body = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html_text)
    body = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", body)
    body = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", body)
    body = re.sub(r"(?is)<!--.*?-->", " ", body)
    body = re.sub(r"(?i)</?(p|div|section|article|li|ul|ol|tr|table|blockquote|h1|h2|h3|h4|h5|h6|br)[^>]*>", "\n", body)
    body = re.sub(r"(?i)</?(td|th)[^>]*>", " ", body)
    body = re.sub(r"(?is)<[^>]+>", " ", body)
    return body


def _normalize_preview_line(line: str) -> str:
    value = line.strip()
    value = re.sub(r"\s*[|/]+\s*", " ", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" -|/")


def _is_preview_noise(line: str) -> bool:
    if not line:
        return True
    if len(line) <= 2:
        return True

    lowered = line.lower()
    noise_fragments = [
        "doctype html",
        "当前位置",
        "设为首页",
        "加入收藏",
        "手机版",
        "繁体",
        "无障碍",
        "长者模式",
        "搜索",
        "首页",
        "时政要闻",
        "网信政务",
        "互动服务",
        "热点专题",
        "copyright",
        "header",
        "footer",
        "来源：",
        "作者：",
        "日期：",
        "发布时间",
        "打印",
        "纠错",
    ]
    if any(fragment in lowered for fragment in noise_fragments):
        return True

    if re.search(r"[{};]|font-size|line-height|margin-top|display\s*:|float\s*:|padding\s*:|background\s*:", lowered):
        return True

    if not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", line):
        return True

    meaningful = sum(1 for char in line if char.isalnum() or "\u4e00" <= char <= "\u9fff")
    if meaningful < 4:
        return True

    return False


def _select_preview_start(lines: list[str]) -> int:
    best_index = 0
    best_score = float("-inf")
    for idx, line in enumerate(lines):
        score = _preview_line_score(line)
        if idx + 1 < len(lines):
            score += _preview_line_score(lines[idx + 1]) * 0.35
        if idx + 2 < len(lines):
            score += _preview_line_score(lines[idx + 2]) * 0.2
        if score > best_score:
            best_score = score
            best_index = idx
    for lookback in (2, 1):
        candidate = best_index - lookback
        if candidate >= 0 and _is_preview_lead_line(lines[candidate]):
            return candidate
    return best_index


def _preview_line_score(line: str) -> float:
    score = 0.0
    length = len(line)
    if length >= 18:
        score += 2.5
    elif length >= 10:
        score += 1.0

    if re.search(r"[。；：!?]|《|》", line):
        score += 2.5
    if re.search(r"^第[一二三四五六七八九十百千零\d]+条", line):
        score += 3.0
    if re.search(r"^[一二三四五六七八九十]+、", line):
        score += 2.0
    if re.search(r"（[一二三四五六七八九十\d]+）", line):
        score += 1.5
    if re.search(r"(办法|规定|指南|合同|评估|个人信息|数据出境|风险|申报|案例)", line):
        score += 2.0
    if re.search(r"^(来源|作者|日期|主办|承办|技术支持|京ICP备|津ICP备|版权所有)", line):
        score -= 4.0
    if length <= 6:
        score -= 1.5
    return score


def _is_preview_footer(line: str) -> bool:
    return bool(
        re.search(
            r"^(主办|承办|技术支持|政府网站标识码|京ICP备|津ICP备|京公网安备|版权所有|联系我们|ICP备)",
            line,
        )
    )


def _is_preview_lead_line(line: str) -> bool:
    if len(line) > 40:
        return False
    if re.search(r"^(来源|作者|日期|主办|承办|技术支持)", line):
        return False
    if re.search(r"^第[一二三四五六七八九十百千零\d]+条", line):
        return True
    if re.search(r"^[一二三四五六七八九十]+、", line):
        return True
    if re.search(r"(办法|规定|指南|合同|评估|个人信息|数据出境|案例)", line):
        return True
    if not re.search(r"[。！？；：]", line) and len(line) >= 8:
        return True
    return False


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
