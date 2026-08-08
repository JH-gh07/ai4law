from __future__ import annotations

import csv
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

from backend.common.citation.locators import normalize_article_no
from backend.common.knowledge.paths import regulation_articles_jsonl_path, sources_csv_path

# ── 知识库 source_id 注册表（title → source_id 反向查找）──────────────

_SOURCES_CSV_PATH = sources_csv_path()
_REGULATION_ARTICLES_PATH = regulation_articles_jsonl_path()

_KNOWN_SOURCE_IDS: set[str] = set()
_TITLE_TO_SOURCE_ID: dict[str, str] = {}
_TITLE_WORDS_TO_SOURCE_IDS: dict[str, list[tuple[str, float]]] = {}
_SOURCE_METADATA_BY_ID: dict[str, dict[str, str]] = {}
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
    global _KNOWN_SOURCE_IDS, _TITLE_TO_SOURCE_ID, _TITLE_WORDS_TO_SOURCE_IDS, _SOURCE_METADATA_BY_ID, _SOURCES_CSV_LOADED
    if _SOURCES_CSV_LOADED:
        return
    if not _SOURCES_CSV_PATH.exists():
        _SOURCES_CSV_LOADED = True
        return

    with open(_SOURCES_CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = (row.get("source_id") or row.get("id") or "").strip()
            title = (row.get("title") or "").strip()
            if not sid:
                continue
            _KNOWN_SOURCE_IDS.add(sid)
            _SOURCE_METADATA_BY_ID[sid] = {
                "title": title,
                "url": (row.get("url") or "").strip(),
                "publish_date": (row.get("publish_date") or "").strip(),
                "effective_date": (row.get("effective_date") or "").strip(),
                "status": (row.get("status") or "").strip(),
            }
            if not title:
                continue
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
    """Compatibility wrapper for the shared canonical locator normalizer."""
    return normalize_article_no(article_no)


@lru_cache(maxsize=1)
def _load_article_index() -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], str]]:
    """Return locator match counts and safe article-level official URLs."""
    counts: dict[tuple[str, str], int] = {}
    source_urls: dict[tuple[str, str], str] = {}
    if not _REGULATION_ARTICLES_PATH.exists():
        return counts, source_urls
    with _REGULATION_ARTICLES_PATH.open(encoding="utf-8") as fp:
        for line in fp:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            source_id = str(row.get("source_id", "") or "").strip()
            article_no = _normalize_article_no(str(row.get("article_ref", "") or ""))
            if not source_id or not article_no:
                continue
            key = (source_id, article_no)
            counts[key] = counts.get(key, 0) + 1
            source_url = str(row.get("source_url", "") or "").strip()
            if key not in source_urls and _is_safe_external_url(source_url):
                source_urls[key] = source_url
    return counts, source_urls


def _load_article_counts() -> dict[tuple[str, str], int]:
    return _load_article_index()[0]


def _load_article_source_urls() -> dict[tuple[str, str], str]:
    return _load_article_index()[1]


def _is_safe_external_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_recent_effective_date(value: str, *, as_of: date | None = None) -> bool:
    try:
        effective = date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    today = as_of or date.today()
    age_days = (today - effective).days
    return 0 <= age_days <= 366


def _extract_amendment_note(title: str) -> str:
    match = re.search(r"(\d{4}年?(?:修正|修订))", title or "")
    return match.group(1).replace("年", "") if match else ""


def _resolve_citation_target(
    *,
    source_id: str,
    article_no: str,
    source_url: str,
    external_verified: bool,
    citation_granularity: str,
) -> dict[str, Any]:
    """Resolve a citation against the local registry without trusting cached hints."""
    _load_sources_csv()
    source_known = source_id in _KNOWN_SOURCE_IDS
    safe_external_url = source_url if _is_safe_external_url(source_url) else ""

    if source_known and citation_granularity == "source":
        actions = ["view_source_overview", "search_within_source"]
        if safe_external_url:
            actions.append("open_official_source")
        return {
            "resolution_type": "source_overview",
            "target_id": source_id,
            "confidence": 0.7,
            "failure_reason": "source_level_by_design",
            "available_actions": actions,
        }

    if source_known and article_no:
        match_count = _load_article_counts().get((source_id, article_no), 0)
        if match_count == 1:
            actions = ["view_article", "view_source_overview"]
            if safe_external_url:
                actions.append("open_official_source")
            return {
                "resolution_type": "exact_article",
                "target_id": f"{source_id}:{article_no}",
                "confidence": 1.0,
                "failure_reason": "",
                "available_actions": actions,
            }
        failure_reason = "article_not_unique" if match_count > 1 else "article_not_found"
        actions = ["view_source_overview", "search_within_source"]
        if safe_external_url:
            actions.append("open_official_source")
        return {
            "resolution_type": "source_overview",
            "target_id": source_id,
            "confidence": 0.6,
            "failure_reason": failure_reason,
            "available_actions": actions,
        }

    if source_known:
        actions = ["view_source_overview", "search_within_source"]
        if safe_external_url:
            actions.append("open_official_source")
        return {
            "resolution_type": "source_overview",
            "target_id": source_id,
            "confidence": 0.7,
            "failure_reason": "article_missing",
            "available_actions": actions,
        }

    if external_verified and safe_external_url:
        return {
            "resolution_type": "external_verified",
            "target_id": safe_external_url,
            "confidence": 0.8,
            "failure_reason": "local_source_not_mapped",
            "available_actions": ["review_external_source", "queue_for_ingestion"],
        }

    return {
        "resolution_type": "unresolved",
        "target_id": "",
        "confidence": 0.0,
        "failure_reason": "source_not_found",
        "available_actions": ["retry_resolution", "manual_review"],
    }


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

    # Normalize article_no to Arabic numerals for consistency with LawViewerPage
    normalized_article_no = _normalize_article_no(article_no) or article_no
    raw_source_url = str(item.get("source_url", "") or "").strip()
    source_metadata = _SOURCE_METADATA_BY_ID.get(resolved_source_id, {})
    article_source_url = _load_article_source_urls().get(
        (resolved_source_id, normalized_article_no),
        "",
    )
    catalog_source_url = str(source_metadata.get("url", "") or "").strip()
    source_url = next(
        (
            candidate
            for candidate in (raw_source_url, article_source_url, catalog_source_url)
            if _is_safe_external_url(candidate)
        ),
        "",
    )
    raw_granularity = str(item.get("citation_granularity", "") or "").strip()
    citation_granularity = (
        "source"
        if not normalized_article_no
        else (raw_granularity if raw_granularity in {"article", "source"} else "article")
    )
    resolution = _resolve_citation_target(
        source_id=resolved_source_id,
        article_no=normalized_article_no,
        source_url=source_url,
        external_verified=item.get("external_verified") is True,
        citation_granularity=citation_granularity,
    )
    resolution_type = str(resolution["resolution_type"])
    if resolution_type == "exact_article":
        knowledge_url = build_knowledge_url(
            source_id=resolved_source_id,
            article_no=normalized_article_no,
        )
    elif resolution_type == "source_overview":
        knowledge_url = build_knowledge_url(source_id=resolved_source_id)
    else:
        knowledge_url = None

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
    normalized["open_mode"] = "in_app"
    normalized["resolution"] = resolution
    normalized["can_jump"] = resolution_type == "exact_article"
    normalized["source_url"] = source_url
    normalized["citation_granularity"] = citation_granularity
    normalized["publish_date"] = str(
        item.get("publish_date") or source_metadata.get("publish_date") or ""
    ).strip()
    normalized["effective_date"] = str(
        item.get("effective_date") or source_metadata.get("effective_date") or ""
    ).strip()
    normalized["source_status"] = str(
        item.get("source_status") or source_metadata.get("status") or ""
    ).strip()
    normalized["is_recent"] = _is_recent_effective_date(normalized["effective_date"])
    normalized["amendment_note"] = str(
        item.get("amendment_note") or _extract_amendment_note(title or source_metadata.get("title", ""))
    ).strip()
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
