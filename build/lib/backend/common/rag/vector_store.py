from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from backend.common.rag.embedding import HashingEmbedder

if TYPE_CHECKING:
    from backend.common.rag.semantic_embedder import SemanticEmbedder


@dataclass
class VectorIndexEntry:
    doc_id: str
    payload: dict
    embedding: dict[int, float]
    search_text: str


class LocalVectorStore:
    def __init__(self, index_path: Path, embedder: HashingEmbedder) -> None:
        self.index_path = index_path
        self.embedder = embedder

    def exists(self) -> bool:
        return self.index_path.exists()

    def save(self, entries: list[VectorIndexEntry], metadata: dict | None = None) -> Path:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(
                {
                    "metadata": metadata or {},
                    "entries": [
                        {
                            "doc_id": entry.doc_id,
                            "payload": entry.payload,
                            "search_text": entry.search_text,
                            "embedding": {str(index): value for index, value in entry.embedding.items()},
                        }
                        for entry in entries
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return self.index_path

    def load(self) -> list[VectorIndexEntry]:
        if not self.exists():
            return []
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        return [
            VectorIndexEntry(
                doc_id=str(row["doc_id"]),
                payload=dict(row.get("payload", {})),
                search_text=str(row.get("search_text", "")),
                embedding={int(index): float(value) for index, value in row.get("embedding", {}).items()},
            )
            for row in data.get("entries", [])
        ]

    def search(self, query_text: str, entries: list[VectorIndexEntry], top_k: int = 12) -> list[tuple[float, VectorIndexEntry]]:
        query_embedding = self.embedder.embed(query_text)
        scored = [
            (self.embedder.similarity(query_embedding, entry.embedding), entry)
            for entry in entries
        ]
        scored = [item for item in scored if item[0] > 0]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:top_k]


# ---------------------------------------------------------------------------
# Dense vector store（语义 Embedding，list[float] 格式）
# ---------------------------------------------------------------------------


@dataclass
class DenseVectorIndexEntry:
    doc_id: str
    payload: dict
    embedding: list[float]
    search_text: str


class DenseVectorStore:
    """稠密向量存储，配合 SemanticEmbedder 使用。"""

    def __init__(self, index_path: Path, embedder: "SemanticEmbedder") -> None:
        self.index_path = index_path
        self.embedder = embedder

    def exists(self) -> bool:
        return self.index_path.exists()

    def save(self, entries: list[DenseVectorIndexEntry], metadata: dict | None = None) -> Path:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(
                {
                    "metadata": {**(metadata or {}), "store_type": "dense"},
                    "entries": [
                        {
                            "doc_id": entry.doc_id,
                            "payload": entry.payload,
                            "search_text": entry.search_text,
                            "embedding": entry.embedding,
                        }
                        for entry in entries
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return self.index_path

    def load(self) -> list[DenseVectorIndexEntry]:
        if not self.exists():
            return []
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        return [
            DenseVectorIndexEntry(
                doc_id=str(row["doc_id"]),
                payload=dict(row.get("payload", {})),
                search_text=str(row.get("search_text", "")),
                embedding=list(row.get("embedding", [])),
            )
            for row in data.get("entries", [])
        ]

    def search(
        self,
        query_text: str,
        entries: list[DenseVectorIndexEntry],
        top_k: int = 12,
    ) -> list[tuple[float, DenseVectorIndexEntry]]:
        q_emb = self.embedder.embed(query_text)
        scored = [
            (self.embedder.similarity(q_emb, entry.embedding), entry)
            for entry in entries
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:top_k]
