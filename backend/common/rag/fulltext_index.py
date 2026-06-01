"""SQLite FTS5 full-text index for regulatory knowledge chunks."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class FulltextIndex:
    """SQLite FTS5 wrapper for knowledge_chunks content search."""

    _fts_initialized: bool = False

    def __init__(self, db: Session) -> None:
        self.db = db
        if not self._fts_initialized:
            self._ensure_fts_table()
            FulltextIndex._fts_initialized = True

    def _ensure_fts_table(self) -> None:
        self.db.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts
            USING fts5(
                chunk_id,
                title,
                content,
                article_no,
                structural_path,
                tokenize='unicode61 remove_diacritics 2'
            )
        """))

    def index_chunk(
        self,
        chunk_id: str,
        title: str,
        content: str,
        article_no: str = "",
        structural_path: str = "",
    ) -> None:
        # Delete existing entry if any
        self.db.execute(
            text("DELETE FROM knowledge_chunks_fts WHERE chunk_id = :cid"),
            {"cid": chunk_id},
        )
        self.db.execute(
            text(
                "INSERT INTO knowledge_chunks_fts(chunk_id, title, content, article_no, structural_path) "
                "VALUES (:cid, :title, :content, :article_no, :path)"
            ),
            {
                "cid": chunk_id,
                "title": title,
                "content": content,
                "article_no": article_no,
                "path": structural_path,
            },
        )
        self.db.commit()

    def rebuild_all(self, chunks: list[dict]) -> None:
        """Rebuild FTS index from a list of chunk dicts."""
        # Drop and recreate
        self.db.execute(text("DROP TABLE IF EXISTS knowledge_chunks_fts"))
        self._ensure_fts_table()
        for chunk in chunks:
            self.index_chunk(
                chunk_id=chunk.get("chunk_id", ""),
                title=chunk.get("title", ""),
                content=chunk.get("content", ""),
                article_no=chunk.get("article_no", ""),
                structural_path=chunk.get("structural_path", ""),
            )

    def search(
        self,
        query: str,
        *,
        doc_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Search knowledge chunks via FTS5.

        Uses simple FTS5 MATCH on content field. For Chinese text,
        the unicode61 tokenizer provides character-level indexing.
        """
        # Sanitize query for FTS5
        safe_query = re.sub(r'[^\w\s一-鿿]', ' ', query or "").strip()
        if not safe_query:
            return []

        try:
            rows = self.db.execute(
                text(
                    "SELECT chunk_id, title, content, article_no, structural_path, "
                    "rank FROM knowledge_chunks_fts WHERE knowledge_chunks_fts MATCH :q "
                    "ORDER BY rank LIMIT :limit OFFSET :offset"
                ),
                {"q": safe_query, "limit": limit, "offset": offset},
            ).fetchall()
        except Exception:
            # FTS5 may fail on malformed queries; fall back to empty
            return []

        results: list[dict] = []
        for row in rows:
            results.append({
                "chunk_id": row[0],
                "title": row[1],
                "content": row[2],
                "article_no": row[3],
                "structural_path": row[4],
                "rank": row[5],
            })
        return results

    def search_article(
        self,
        keyword: str,
        jurisdiction: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search for a specific article number or keyword."""
        return self.search(keyword, jurisdiction=jurisdiction, limit=limit)
