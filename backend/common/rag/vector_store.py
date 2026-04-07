from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.common.rag.embedding import HashingEmbedder


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
