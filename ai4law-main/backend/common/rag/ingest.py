from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from backend.common.rag.embedding import HashingEmbedder
from backend.common.rag.vector_store import LocalVectorStore, VectorIndexEntry

if TYPE_CHECKING:
    from backend.core.settings import Settings


def load_regulation_rows(source_jsonl: Path) -> list[dict]:
    rows: list[dict] = []
    if not source_jsonl.exists():
        return rows
    with source_jsonl.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def build_search_text(row: dict) -> str:
    keywords = " ".join(str(item) for item in row.get("keywords", []))
    return " ".join(
        [
            str(row.get("law_name", "")),
            str(row.get("article_ref", "")),
            str(row.get("content", "")),
            str(row.get("jurisdiction", "")),
            str(row.get("path", "")),
            keywords,
        ]
    ).strip()


def build_regulation_index(settings: Settings, source_jsonl: Path | None = None, output_path: Path | None = None) -> Path:
    source_path = source_jsonl or settings.rag_source_jsonl
    index_path = output_path or settings.rag_index_path

    embedder = HashingEmbedder(settings.rag_embedding_dimension)
    store = LocalVectorStore(index_path=index_path, embedder=embedder)
    rows = load_regulation_rows(source_path)

    entries: list[VectorIndexEntry] = []
    for row in rows:
        payload = {
            "id": str(row.get("article_id", "")),
            "title": str(row.get("law_name", "")),
            "article": str(row.get("article_ref", "")),
            "content": str(row.get("content", "")),
            "jurisdiction": str(row.get("jurisdiction", "")),
            "path": str(row.get("path", "")),
            "doc_type": str(row.get("doc_type", "")),
            "source_url": str(row.get("source_url", "")),
            "snapshot_path": str(row.get("snapshot_path", "")),
            "usage_priority": str(row.get("usage_priority", "P1")),
            "keywords": [str(item) for item in row.get("keywords", []) if str(item).strip()],
        }
        search_text = build_search_text(row)
        entries.append(
            VectorIndexEntry(
                doc_id=payload["id"],
                payload=payload,
                search_text=search_text,
                embedding=embedder.embed(search_text),
            )
        )

    store.save(
        entries,
        metadata={
            "source_jsonl": str(source_path),
            "entry_count": len(entries),
            "embedding_dimension": settings.rag_embedding_dimension,
        },
    )
    return index_path
