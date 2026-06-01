"""PostgreSQL pgvector vector store implementation.

Optional module — only used when database_url points to PostgreSQL.
Falls back gracefully to LocalVectorStore when pgvector is unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from backend.common.rag.embedding import HashingEmbedder
from backend.core.settings import Settings

logger = logging.getLogger(__name__)

_PGVECTOR_AVAILABLE = False
try:
    import pgvector  # noqa: F401

    _PGVECTOR_AVAILABLE = True
except ImportError:
    pass


class PgVectorStore:
    """Vector store backed by PostgreSQL + pgvector extension.

    Creates the extension and table on first use. Vectors are stored
    as pgvector vector(N) type, with metadata in a JSONB column.
    """

    def __init__(
        self,
        settings: Settings,
        embedder: Optional[HashingEmbedder] = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or HashingEmbedder(settings.rag_embedding_dimension)
        self._table_name = "regulation_vectors"
        self._dimension = settings.rag_embedding_dimension

    def _ensure_extension_and_table(self, conn) -> None:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                article TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                jurisdiction TEXT NOT NULL DEFAULT '',
                path TEXT NOT NULL DEFAULT '',
                doc_type TEXT NOT NULL DEFAULT '',
                source_url TEXT NOT NULL DEFAULT '',
                snapshot_path TEXT NOT NULL DEFAULT '',
                keywords TEXT NOT NULL DEFAULT '[]',
                embedding vector({self._dimension})
            )
        """)

    def exists(self) -> bool:
        if not _PGVECTOR_AVAILABLE:
            return False
        try:
            from sqlalchemy import text

            engine = self._get_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT 1 FROM pg_tables WHERE tablename = '{self._table_name}'")
                ).fetchone()
                return result is not None
        except Exception:
            return False

    def _get_engine(self):
        from backend.core.db import build_engine

        return build_engine(self.settings.database_url)

    def load(self) -> list[dict]:
        if not _PGVECTOR_AVAILABLE:
            return []
        try:
            from sqlalchemy import text

            engine = self._get_engine()
            with engine.connect() as conn:
                self._ensure_extension_and_table(conn)
                rows = conn.execute(
                    text(
                        f"SELECT id, title, article, content, jurisdiction, path, "
                        f"doc_type, source_url, snapshot_path, keywords "
                        f"FROM {self._table_name}"
                    )
                ).fetchall()
                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "article": row[2],
                        "content": row[3],
                        "jurisdiction": row[4],
                        "path": row[5],
                        "doc_type": row[6],
                        "source_url": row[7],
                        "snapshot_path": row[8],
                        "keywords": json.loads(row[9]) if row[9] else [],
                    }
                    for row in rows
                ]
        except Exception:
            logger.warning("Failed to load vectors from pgvector", exc_info=True)
            return []

    def save(self, entries: list[dict]) -> None:
        if not _PGVECTOR_AVAILABLE:
            return
        try:
            from sqlalchemy import text

            engine = self._get_engine()
            with engine.begin() as conn:
                self._ensure_extension_and_table(conn)
                for entry in entries:
                    text_to_embed = str(entry.get("content", ""))[:2000]
                    vec = self.embedder.embed(text_to_embed)
                    vec_str = "[" + ",".join(str(v) for v in vec) + "]"
                    conn.execute(
                        text(
                            f"INSERT INTO {self._table_name} "
                            f"(id, title, article, content, jurisdiction, path, "
                            f"doc_type, source_url, snapshot_path, keywords, embedding) "
                            f"VALUES (:id, :title, :article, :content, :jurisdiction, :path, "
                            f":doc_type, :source_url, :snapshot_path, :keywords, :embedding::vector) "
                            f"ON CONFLICT (id) DO UPDATE SET "
                            f"title=EXCLUDED.title, content=EXCLUDED.content, "
                            f"embedding=EXCLUDED.embedding"
                        ),
                        {
                            "id": str(entry.get("id", "")),
                            "title": str(entry.get("title", "")),
                            "article": str(entry.get("article", "")),
                            "content": str(entry.get("content", "")),
                            "jurisdiction": str(entry.get("jurisdiction", "")),
                            "path": str(entry.get("path", "")),
                            "doc_type": str(entry.get("doc_type", "")),
                            "source_url": str(entry.get("source_url", "")),
                            "snapshot_path": str(entry.get("snapshot_path", "")),
                            "keywords": json.dumps(
                                entry.get("keywords", []), ensure_ascii=False
                            ),
                            "embedding": vec_str,
                        },
                    )
        except Exception:
            logger.warning("Failed to save vectors to pgvector", exc_info=True)

    def search(
        self,
        query: str,
        entries: list[dict],
        top_k: int = 24,
    ) -> list[tuple[float, dict]]:
        if not _PGVECTOR_AVAILABLE or not entries:
            return []
        try:
            from sqlalchemy import text

            query_vec = self.embedder.embed(query)
            vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

            engine = self._get_engine()
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        f"SELECT id, title, article, content, jurisdiction, path, "
                        f"doc_type, source_url, snapshot_path, keywords, "
                        f"1 - (embedding <=> :vec::vector) AS similarity "
                        f"FROM {self._table_name} "
                        f"ORDER BY embedding <=> :vec::vector "
                        f"LIMIT :top_k"
                    ),
                    {"vec": vec_str, "top_k": top_k},
                ).fetchall()

                results: list[tuple[float, dict]] = []
                for row in rows:
                    score = float(row[10]) if row[10] else 0.0
                    payload = {
                        "id": row[0],
                        "title": row[1],
                        "article": row[2],
                        "content": row[3],
                        "jurisdiction": row[4],
                        "path": row[5],
                        "doc_type": row[6],
                        "source_url": row[7],
                        "snapshot_path": row[8],
                        "keywords": json.loads(row[9]) if row[9] else [],
                    }
                    results.append((score, payload))
                return results
        except Exception:
            logger.warning("Failed to search vectors in pgvector", exc_info=True)
            return []


def create_vector_store(
    settings: Settings,
    embedder: Optional[HashingEmbedder] = None,
):
    """Factory: returns PgVectorStore if PostgreSQL is configured, else LocalVectorStore."""
    db_url = (settings.database_url or "").lower()
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        if _PGVECTOR_AVAILABLE:
            logger.info("Using PgVectorStore for PostgreSQL database")
            return PgVectorStore(settings, embedder=embedder)
        logger.warning(
            "PostgreSQL configured but pgvector package not installed. "
            "Falling back to LocalVectorStore."
        )

    from backend.common.rag.vector_store import LocalVectorStore

    return LocalVectorStore(settings.rag_index_path, embedder=embedder or HashingEmbedder(settings.rag_embedding_dimension))
