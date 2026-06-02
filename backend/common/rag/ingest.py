from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from backend.common.rag.constants import MULTI_INDEX_SCHEMA_VERSION
from backend.common.rag.orchestrator import INDEX_NAMES, build_chunk_sets
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


def build_multi_index_v3(settings: Settings) -> dict[str, Path]:
    rag_dir = settings.rag_v3_dir
    rag_dir.mkdir(parents=True, exist_ok=True)
    embedder = HashingEmbedder(settings.rag_embedding_dimension)
    chunk_sets = build_chunk_sets()
    outputs: dict[str, Path] = {}

    for index_name in INDEX_NAMES:
        chunks = chunk_sets.get(index_name, [])
        vector_path = rag_dir / f"{index_name}.vector.json"
        jsonl_path = rag_dir / f"{index_name}.jsonl"
        entries: list[VectorIndexEntry] = []
        rows: list[dict] = []
        for chunk in chunks:
            payload = chunk.to_payload()
            rows.append(payload)
            search_text = " ".join(
                [
                    chunk.title,
                    chunk.content,
                    chunk.citation_anchor,
                    " ".join(chunk.reference_ids),
                    " ".join(chunk.scenario_tags),
                    " ".join(chunk.keywords),
                ]
            ).strip()
            entries.append(
                VectorIndexEntry(
                    doc_id=chunk.chunk_id,
                    payload=payload,
                    search_text=search_text,
                    embedding=embedder.embed(search_text),
                )
            )
        LocalVectorStore(index_path=vector_path, embedder=embedder).save(
            entries,
            metadata={
                "index_name": index_name,
                "entry_count": len(entries),
                "schema_version": MULTI_INDEX_SCHEMA_VERSION,
            },
        )
        jsonl_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
            encoding="utf-8",
        )
        outputs[index_name] = vector_path
    return outputs
