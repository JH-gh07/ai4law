"""Knowledge base review pipeline API.

Endpoints for human-in-the-loop review of ingested regulatory documents.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.common.knowledge.models import IngestedFile, KnowledgeChunk, KnowledgeDocument
from backend.core.db import build_engine, build_session_factory
from backend.core.settings import Settings, get_settings

router = APIRouter()


class ReviewQueueItem(BaseModel):
    id: int
    title: str
    doc_type: str
    jurisdiction: str
    source: str
    status: str
    chunk_count: int = 0
    uploaded_at: str = ""


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int


class ChunkUpdateRequest(BaseModel):
    content: str | None = None
    article_no: str | None = None
    structural_level: str | None = None
    review_status: str | None = None


class ChunkResponse(BaseModel):
    id: int
    chunk_id: str
    document_id: int
    article_no: str
    title: str
    content: str
    structural_level: str
    structural_path: str
    review_status: str


class ApproveResponse(BaseModel):
    doc_id: int
    status: str


class PublishResponse(BaseModel):
    doc_id: int
    status: str


def _get_db() -> Session:
    settings = get_settings()
    engine = build_engine(settings.database_url)
    factory = build_session_factory(engine)
    return factory()


@router.get("/queue", response_model=ReviewQueueResponse)
def get_review_queue(
    status: str = Query(default="review_pending"),
    jurisdiction: str | None = Query(default=None),
    doc_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(_get_db),
) -> ReviewQueueResponse:
    q = db.query(KnowledgeDocument)
    if status:
        q = q.filter(KnowledgeDocument.review_status == status)
    if jurisdiction:
        q = q.filter(KnowledgeDocument.jurisdiction == jurisdiction)
    if doc_type:
        q = q.filter(KnowledgeDocument.doc_type == doc_type)
    if source:
        q = q.filter(KnowledgeDocument.source == source)

    total = q.count()
    docs = q.order_by(KnowledgeDocument.created_at.desc()).offset(offset).limit(limit).all()

    items: list[ReviewQueueItem] = []
    for doc in docs:
        chunk_count = (
            db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.document_id == doc.id)
            .count()
        )
        uploaded_at = ""
        ingested = (
            db.query(IngestedFile)
            .filter(IngestedFile.document_id == doc.id)
            .first()
        )
        if ingested:
            uploaded_at = ingested.uploaded_at.isoformat() if ingested.uploaded_at else ""

        items.append(
            ReviewQueueItem(
                id=doc.id,
                title=doc.title,
                doc_type=doc.doc_type,
                jurisdiction=doc.jurisdiction,
                source=doc.source,
                status=doc.review_status,
                chunk_count=chunk_count,
                uploaded_at=uploaded_at,
            )
        )

    return ReviewQueueResponse(items=items, total=total)


@router.get("/queue/{doc_id}", response_model=ReviewQueueItem)
def get_review_document(
    doc_id: int,
    db: Session = Depends(_get_db),
) -> ReviewQueueItem:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    chunk_count = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == doc.id)
        .count()
    )
    uploaded_at = ""
    ingested = (
        db.query(IngestedFile)
        .filter(IngestedFile.document_id == doc.id)
        .first()
    )
    if ingested:
        uploaded_at = ingested.uploaded_at.isoformat() if ingested.uploaded_at else ""

    return ReviewQueueItem(
        id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type,
        jurisdiction=doc.jurisdiction,
        source=doc.source,
        status=doc.review_status,
        chunk_count=chunk_count,
        uploaded_at=uploaded_at,
    )


@router.get("/queue/{doc_id}/chunks", response_model=list[ChunkResponse])
def get_document_chunks(
    doc_id: int,
    db: Session = Depends(_get_db),
) -> list[ChunkResponse]:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == doc_id)
        .order_by(KnowledgeChunk.id)
        .all()
    )
    return [
        ChunkResponse(
            id=chunk.id,
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            article_no=chunk.article_no,
            title=chunk.title,
            content=chunk.content,
            structural_level=chunk.structural_level,
            structural_path=chunk.structural_path,
            review_status=chunk.review_status,
        )
        for chunk in chunks
    ]


@router.put("/chunks/{chunk_id}", response_model=ChunkResponse)
def update_chunk(
    chunk_id: int,
    body: ChunkUpdateRequest,
    db: Session = Depends(_get_db),
) -> ChunkResponse:
    chunk = db.query(KnowledgeChunk).filter(KnowledgeChunk.id == chunk_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk not found: {chunk_id}")

    if body.content is not None:
        chunk.content = body.content
    if body.article_no is not None:
        chunk.article_no = body.article_no
    if body.structural_level is not None:
        chunk.structural_level = body.structural_level
    if body.review_status is not None:
        chunk.review_status = body.review_status

    db.commit()
    db.refresh(chunk)

    return ChunkResponse(
        id=chunk.id,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        article_no=chunk.article_no,
        title=chunk.title,
        content=chunk.content,
        structural_level=chunk.structural_level,
        structural_path=chunk.structural_path,
        review_status=chunk.review_status,
    )


@router.post("/{doc_id}/approve", response_model=ApproveResponse)
def approve_document(
    doc_id: int,
    db: Session = Depends(_get_db),
) -> ApproveResponse:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    doc.review_status = "reviewed"
    db.query(IngestedFile).filter(IngestedFile.document_id == doc_id).update(
        {"status": "reviewed"}
    )
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).update(
        {"review_status": "reviewed"}
    )
    db.commit()

    return ApproveResponse(doc_id=doc_id, status="reviewed")


@router.post("/{doc_id}/publish", response_model=PublishResponse)
def publish_document(
    doc_id: int,
    db: Session = Depends(_get_db),
) -> PublishResponse:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    doc.review_status = "published"
    db.query(IngestedFile).filter(IngestedFile.document_id == doc_id).update(
        {"status": "published"}
    )
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).update(
        {"review_status": "published"}
    )

    # Index chunks into FTS5 for search
    from backend.common.rag.fulltext_index import FulltextIndex

    published_chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == doc_id)
        .all()
    )
    if published_chunks:
        fts = FulltextIndex(db)
        for chunk in published_chunks:
            fts.index_chunk(
                chunk_id=chunk.chunk_id,
                title=chunk.title,
                content=chunk.content,
                article_no=chunk.article_no,
                structural_path=chunk.structural_path,
            )

    db.commit()

    return PublishResponse(doc_id=doc_id, status="published")


@router.post("/{doc_id}/reject", response_model=ApproveResponse)
def reject_document(
    doc_id: int,
    db: Session = Depends(_get_db),
) -> ApproveResponse:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    doc.review_status = "rejected"
    db.query(IngestedFile).filter(IngestedFile.document_id == doc_id).update(
        {"status": "rejected"}
    )
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).update(
        {"review_status": "rejected"}
    )
    db.commit()

    return ApproveResponse(doc_id=doc_id, status="rejected")
