from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


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
        query["article"] = article_no
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
    article_no = str(item.get("article_no", "") or "")
    anchor = str(item.get("anchor") or item.get("citation_anchor") or "")
    section_id = str(item.get("section_id", "") or "")
    clause_id = str(item.get("clause_id", "") or "")
    knowledge_url = item.get("knowledge_url")
    if not isinstance(knowledge_url, str) or not knowledge_url.strip():
        knowledge_url = build_knowledge_url(
            source_id=source_id,
            article_no=article_no,
            anchor=anchor,
            section_id=section_id,
            clause_id=clause_id,
        )

    can_jump = bool(source_id and knowledge_url)
    normalized = dict(item)
    normalized["module"] = module
    normalized["source_id"] = source_id
    normalized["article_no"] = article_no
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
    return value.split("第")[0].strip("：《》[]【】()（） ") or value


def _citation_article_from_source(source: str) -> str:
    value = (source or "").strip()
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
            if not citation_text:
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
