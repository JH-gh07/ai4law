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
