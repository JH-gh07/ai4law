from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base
from backend.core.time import utc_now_naive


class IngestStatus(str, Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    chunked = "chunked"
    indexed = "indexed"
    review_pending = "review_pending"
    reviewed = "reviewed"
    published = "published"
    rejected = "rejected"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    publisher: Mapped[str] = mapped_column(String(256), default="")
    publish_date: Mapped[str] = mapped_column(String(32), default="")
    effective_date: Mapped[str] = mapped_column(String(32), default="")
    doc_type: Mapped[str] = mapped_column(String(64), default="law")
    jurisdiction: Mapped[str] = mapped_column(String(16), default="cn")
    authority_level: Mapped[str] = mapped_column(String(32), default="medium")
    binding_force: Mapped[str] = mapped_column(String(32), default="recommended")
    review_status: Mapped[str] = mapped_column(String(32), default="review_pending")
    source: Mapped[str] = mapped_column(String(32), default="regulatory")
    user_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class IngestedFile(Base):
    __tablename__ = "ingested_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    original_name: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))
    jurisdiction: Mapped[str] = mapped_column(String(16), default="cn")
    doc_type: Mapped[str] = mapped_column(String(64), default="law")
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    source: Mapped[str] = mapped_column(String(32), default="regulatory")
    user_id: Mapped[str] = mapped_column(String(64), default="")
    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, index=True)
    file_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    article_no: Mapped[str] = mapped_column(String(32), default="")
    title: Mapped[str] = mapped_column(String(512), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    structural_level: Mapped[str] = mapped_column(String(32), default="article")
    structural_path: Mapped[str] = mapped_column(String(1024), default="")
    parent_chunk_ids: Mapped[str] = mapped_column(String(1024), default="")
    page_no: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    source: Mapped[str] = mapped_column(String(32), default="regulatory")
