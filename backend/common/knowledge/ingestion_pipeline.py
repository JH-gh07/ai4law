"""Regulatory document ingestion pipeline.

Orchestrates: save → parse → chunk → store metadata → embed → index.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.common.knowledge.chunker import ChineseLegalChunker
from backend.common.knowledge.document_parser import DocumentParser
from backend.common.knowledge.models import IngestedFile, KnowledgeChunk, KnowledgeDocument
from backend.common.knowledge.storage_manager import KnowledgeStorageManager
from backend.core.time import utc_now_naive


class IngestionPipeline:
    """Orchestrate the full ingestion flow for a regulatory document."""

    def __init__(
        self,
        storage: KnowledgeStorageManager | None = None,
        parser: DocumentParser | None = None,
    ) -> None:
        self.storage = storage or KnowledgeStorageManager()
        self.parser = parser or DocumentParser()

    def ingest(
        self,
        file_bytes: bytes,
        filename: str,
        db: Session,
        *,
        jurisdiction: str = "cn",
        doc_type: str = "law",
        source: str = "regulatory",
        user_id: str = "",
        auto_publish: bool = False,
    ) -> int:
        """Run the full ingestion pipeline and return the document_id."""
        # 1. Save original file (hash dedup)
        file_hash, storage_path, is_dup = self.storage.save(
            file_bytes, filename,
            jurisdiction=jurisdiction,
            doc_type=doc_type,
            source=source,
            user_id=user_id,
        )

        # Record ingested file
        ingested = IngestedFile(
            file_hash=file_hash,
            original_name=filename,
            storage_path=str(storage_path),
            jurisdiction=jurisdiction,
            doc_type=doc_type,
            status="uploaded",
            source=source,
            user_id=user_id,
            uploaded_at=utc_now_naive(),
        )
        db.add(ingested)
        db.flush()

        if is_dup:
            existing = db.query(IngestedFile).filter(
                IngestedFile.file_hash == file_hash,
                IngestedFile.id != ingested.id,
            ).first()
            if existing and existing.document_id:
                return existing.document_id

        # 2. Parse
        parsed = self.parser.parse_bytes(file_bytes, filename)
        ingested.status = "parsed"

        # 3. Create knowledge document
        review_status = "published" if auto_publish else "review_pending"
        doc = KnowledgeDocument(
            title=parsed.title or filename,
            publisher=parsed.publisher,
            publish_date=parsed.publish_date,
            effective_date=parsed.effective_date,
            doc_type=doc_type,
            jurisdiction=jurisdiction,
            review_status=review_status,
            source=source,
            user_id=user_id,
        )
        db.add(doc)
        db.flush()

        ingested.document_id = doc.id
        ingested.status = "chunked"

        # 4. Chunk
        source_id = f"CN-{doc_type.upper()}-{doc.id:03d}" if jurisdiction == "cn" else f"{jurisdiction.upper()}-{doc_type.upper()}-{doc.id:03d}"
        chunker = ChineseLegalChunker(source_id=source_id, title=parsed.title)
        legal_chunks = chunker.chunk(parsed.raw_text)

        for lc in legal_chunks:
            kc = KnowledgeChunk(
                chunk_id=lc.chunk_id,
                document_id=doc.id,
                file_id=ingested.id,
                article_no=lc.article_no,
                title=parsed.title,
                content=lc.content,
                structural_level=lc.structural_level,
                structural_path=lc.structural_path,
                parent_chunk_ids=";".join(lc.parent_chunk_ids),
                page_no=lc.page_no,
                review_status=review_status,
                source=source,
            )
            db.add(kc)

        ingested.status = "review_pending" if not auto_publish else "published"
        db.commit()

        return doc.id
