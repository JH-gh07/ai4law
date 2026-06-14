from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

# ── 知识库 source_id 注册表（title → source_id 反向查找）──────────────

_SOURCES_CSV_PATH = Path("doc/knowledge/_index/sources.csv")
_LEGACY_SOURCES_CSV_PATH = Path("doc/knowledge/index/sources.csv")

_KNOWN_SOURCE_IDS: set[str] = set()
_TITLE_TO_SOURCE_ID: dict[str, str] = {}
_TITLE_WORDS_TO_SOURCE_IDS: dict[str, list[tuple[str, float]]] = {}
_SOURCES_CSV_LOADED = False


def _normalize_title_key(title: str) -> str:
    """Normalize a title for fuzzy lookup."""
    return (title or "").replace("《", "").replace("》", "").replace("（", "(").replace("）", ")").strip().lower()


def _word_overlap(a: str, b: str) -> float:
    """Jaccard-like overlap between two strings."""
    words_a = set(w for w in a.replace("(", " ").replace(")", " ").replace("-", " ").split() if len(w) >= 2)
    words_b = set(w for w in b.replace("(", " ").replace(")", " ").replace("-", " ").split() if len(w) >= 2)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))


def _load_sources_csv() -> None:
    """Load sources.csv and build title → source_id lookup tables (called once)."""
    global _KNOWN_SOURCE_IDS, _TITLE_TO_SOURCE_ID, _TITLE_WORDS_TO_SOURCE_IDS, _SOURCES_CSV_LOADED
    if _SOURCES_CSV_LOADED:
        return
    csv_path = _SOURCES_CSV_PATH if _SOURCES_CSV_PATH.exists() else _LEGACY_SOURCES_CSV_PATH
    if not csv_path.exists():
        _SOURCES_CSV_LOADED = True
        return

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = (row.get("source_id") or row.get("id") or "").strip()
            title = (row.get("title") or "").strip()
            if not sid or not title:
                continue
            _KNOWN_SOURCE_IDS.add(sid)
            norm_title = _normalize_title_key(title)
            if norm_title and norm_title not in _TITLE_TO_SOURCE_ID:
                _TITLE_TO_SOURCE_ID[norm_title] = sid
            # Short form: title before first bracket
            short = norm_title.split("(")[0].split("（")[0].strip()
            if short and short != norm_title:
                if short not in _TITLE_TO_SOURCE_ID or len(short) > len(list(_TITLE_TO_SOURCE_ID.keys())[0]):
                    _TITLE_TO_SOURCE_ID[short] = sid

    # Build word-overlap index for fallback fuzzy matching
    for norm_title, sid in _TITLE_TO_SOURCE_ID.items():
        for word in norm_title.split():
            word = word.strip("()（）")
            if len(word) >= 3:
                if word not in _TITLE_WORDS_TO_SOURCE_IDS:
                    _TITLE_WORDS_TO_SOURCE_IDS[word] = []
                _TITLE_WORDS_TO_SOURCE_IDS[word].append((norm_title, 1.0))

    _SOURCES_CSV_LOADED = True


@lru_cache(maxsize=1024)
def _resolve_source_id(source_id: str, title: str) -> str:
    """Resolve a source_id to a canonical file ID from sources.csv.

    If source_id is already a known file ID (e.g. CN-LAW-001), return it as-is.
    Otherwise, try fuzzy matching the title against sources.csv to find the
    correct file ID. This fixes the case where citation_map.json stores raw
    Chinese titles instead of file IDs.
    """
    _load_sources_csv()

    # Already a valid source_id
    if source_id in _KNOWN_SOURCE_IDS:
        return source_id

    # Try exact normalized title match
    candidate = title or source_id
    norm = _normalize_title_key(candidate)
    if norm in _TITLE_TO_SOURCE_ID:
        return _TITLE_TO_SOURCE_ID[norm]

    # Try short form (before first bracket)
    short = norm.split("(")[0].split("（")[0].strip()
    if short and short in _TITLE_TO_SOURCE_ID:
        return _TITLE_TO_SOURCE_ID[short]

    # Try substring / word overlap match
    best_sid: str | None = None
    best_score = 0.0
    for known_title, sid in _TITLE_TO_SOURCE_ID.items():
        # Substring match
        if norm and (norm in known_title or known_title in norm):
            score = len(norm) / max(len(known_title), 1)
            if score > best_score:
                best_score = score
                best_sid = sid

    if best_sid and best_score >= 0.3:
        return best_sid

    # Try word overlap fallback
    for known_title, sid in _TITLE_TO_SOURCE_ID.items():
        score = _word_overlap(norm, known_title)
        if score > best_score and score >= 0.5:
            best_score = score
            best_sid = sid

    if best_sid and best_score >= 0.5:
        return best_sid

    # Could not resolve — return original source_id as-is
    return source_id


def _normalize_article_no(article_no: str) -> str:
    """Convert Chinese-numeral article number (六十六) to Arabic (66).

    LawViewerPage and get_article_detail expect Arabic numerals for lookup.
    Passing Chinese numerals in the URL query string causes a mismatch —
    the backend can convert them but keeping Arabic in the URL is the
    canonical form and avoids any client-side parsing difference.
    """
    value = (article_no or "").strip()
    if not value:
        return ""
    if value.isdigit():
        return value
    # Try "第X条" pattern first
    match = re.search(r"第\s*([0-9]+|[零〇一二两三四五六七八九十百千万]+)\s*条", value)
    if match:
        raw_num = match.group(1)
    else:
        raw_num = value
    if raw_num.isdigit():
        return raw_num
    # Try Chinese numeral conversion using the same algorithm as knowledge_index.py
    digit_map: dict[str, int] = {
        "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3,
        "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    }
    unit_map: dict[str, int] = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    total = 0
    section = 0
    number = 0
    for char in raw_num:
        if char in digit_map:
            number = digit_map[char]
        elif char in unit_map:
            unit = unit_map[char]
            if unit == 10000:
                section = (section + (number or 0)) * unit
                total += section
                section = 0
                number = 0
            else:
                if number == 0:
                    number = 1
                section += number * unit
                number = 0
    result = total + section + number
    return str(result) if result > 0 else value


def build_knowledge_url(
    *,
    source_id: str,
    article_no: str = "",
    anchor: str = "",
    section_id: str = "",
    clause_id: str = "",
) -> str | None:
    source = (source_id or "").strip()
    if not source:
        return None

    query: dict[str, str] = {}
    if article_no:
        query["article"] = _normalize_article_no(article_no)
    elif section_id:
        query["section"] = section_id
    elif clause_id:
        query["clause"] = clause_id
    elif anchor:
        query["anchor"] = anchor

    suffix = f"?{urlencode(query)}" if query else ""
    return f"/knowledge/laws/{source}{suffix}"


def normalize_citation_item(item: dict[str, Any], *, module: str) -> dict[str, Any]:
    source_id = str(item.get("source_id", "") or "")
    title = str(item.get("title", "") or "")
    article_no = str(item.get("article_no", "") or "")
    anchor = str(item.get("anchor") or item.get("citation_anchor") or "")
    section_id = str(item.get("section_id", "") or "")
    clause_id = str(item.get("clause_id", "") or "")

    # ── Resolve source_id via title→fileId lookup ──
    resolved_source_id = _resolve_source_id(source_id, title)

    # Always regenerate knowledge_url from the canonical source_id + article_no.
    # Never trust cached values from citation_map.json — old runs may have written
    # stale/wrong URLs (external HTML, /evidence, empty, etc.) that survive the
    # previous conditional-regeneration logic when source_id doesn't change.
    knowledge_url = build_knowledge_url(
        source_id=resolved_source_id,
        article_no=article_no,
        anchor=anchor,
        section_id=section_id,
        clause_id=clause_id,
    )

    # Normalize article_no to Arabic numerals for consistency with LawViewerPage
    normalized_article_no = _normalize_article_no(article_no) or article_no

    can_jump = bool(resolved_source_id and knowledge_url)
    normalized = dict(item)
    normalized["module"] = module
    normalized["source_id"] = resolved_source_id
    normalized["jurisdiction"] = str(item.get("jurisdiction", "") or "")
    normalized["display_label"] = str(item.get("display_label", "") or "")
    normalized["article_no"] = normalized_article_no
    normalized["anchor"] = anchor
    normalized["section_id"] = section_id
    normalized["clause_id"] = clause_id
    normalized["knowledge_url"] = knowledge_url or ""
    normalized["open_mode"] = str(item.get("open_mode") or "new_tab")
    normalized["can_jump"] = bool(item.get("can_jump", can_jump))
    normalized["source_url"] = str(item.get("source_url", "") or "")
    return normalized


def _citation_title_from_source(source: str) -> str:
    value = (source or "").strip()
    if not value:
        return "引用依据"
    if "§" in value:
        return value.split("§", 1)[0].strip("：《》[]【】()（） ") or value
    if "Art." in value or "Article" in value:
        return value.split("Art.", 1)[0].split("Article", 1)[0].strip("：《》[]【】()（） ") or value
    return value.split("第")[0].strip("：《》[]【】()（） ") or value


def _citation_article_from_source(source: str) -> str:
    value = (source or "").strip()
    if "§" in value:
        after = value.split("§", 1)[1]
        return after.strip()
    if "Art." in value:
        after = value.split("Art.", 1)[1]
        return after.strip()
    if "Article" in value:
        after = value.split("Article", 1)[1]
        return after.strip()
    if "第" in value and "条" in value:
        after = value.split("第", 1)[1]
        return after.split("条", 1)[0].strip()
    return ""


def synthesize_citation_map(
    *,
    module: str,
    task_id: str,
    payload: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return {}, []

    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_item(item: dict[str, Any]) -> None:
        normalized = normalize_citation_item(item, module=module)
        key = (
            normalized.get("title", ""),
            normalized.get("article_no", ""),
            normalized.get("quote_text", ""),
            normalized.get("source_id", ""),
        )
        if key in seen:
            return
        seen.add(key)
        items.append(normalized)

    for reg in payload.get("regulations", []) or []:
        if not isinstance(reg, dict):
            continue
        title = str(reg.get("title", "") or "").strip()
        article_no = str(reg.get("article", "") or "").strip()
        snippet = str(reg.get("snippet", "") or "").strip()
        source_id = str(reg.get("source_id", "") or "").strip()
        add_item(
            {
                "citation_id": f"{module}-{task_id}-reg-{len(items) + 1}",
                "source_id": source_id or title,
                "citation_type": "law_article",
                "title": title or "引用法规",
                "article_no": article_no,
                "quote_text": snippet,
                "authority_level": "high",
                "binding_force": "mandatory",
            }
        )

    for chapter in payload.get("chapters", []) or []:
        if not isinstance(chapter, dict):
            continue
        chapter_title = str(chapter.get("title", "") or "").strip()
        citations = chapter.get("citations", []) or []
        if not isinstance(citations, list):
            citations = []
        for raw_citation in citations:
            citation_text = str(raw_citation or "").strip()
            if not citation_text or citation_text.startswith("CIT-"):
                continue
            add_item(
                {
                    "citation_id": f"{module}-{task_id}-chapter-{len(items) + 1}",
                    "source_id": _citation_title_from_source(citation_text),
                    "citation_type": "law_article",
                    "title": _citation_title_from_source(citation_text),
                    "article_no": _citation_article_from_source(citation_text),
                    "quote_text": chapter_title,
                    "authority_level": "medium",
                    "binding_force": "recommended",
                }
            )

    result = payload.get("result")
    if isinstance(result, dict):
        for citation in result.get("citations", []) or []:
            if not isinstance(citation, dict):
                continue
            source = str(citation.get("source") or citation.get("source_title") or "").strip()
            article = str(citation.get("article") or "").strip()
            note = str(citation.get("note") or citation.get("snippet") or "").strip()
            add_item(
                {
                    "citation_id": f"{module}-{task_id}-result-{len(items) + 1}",
                    "source_id": source or _citation_title_from_source(source),
                    "citation_type": "law_article",
                    "title": source or "引用依据",
                    "article_no": article or _citation_article_from_source(source),
                    "quote_text": note,
                }
            )

    footnote_map = {
        str(index): item
        for index, item in enumerate(items, start=1)
    }
    return footnote_map, items


def write_citation_map_json(
    *,
    output_dir: Path,
    module: str,
    task_id: str,
    footnote_map: dict[str, dict[str, Any]] | None = None,
    all_items: list[dict[str, Any]] | None = None,
) -> str:
    normalized_footnote_map: dict[str, dict[str, Any]] = {}
    for num, item in (footnote_map or {}).items():
        normalized_footnote_map[str(num)] = normalize_citation_item(item, module=module)

    normalized_all_items = [
        normalize_citation_item(item, module=module)
        for item in (all_items or [])
    ]

    payload = {
        "task_id": task_id,
        "module": module,
        "footnote_map": normalized_footnote_map,
        "all_items": normalized_all_items,
    }
    path = output_dir / "citation_map.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
