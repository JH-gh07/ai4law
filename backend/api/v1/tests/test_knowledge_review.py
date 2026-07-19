"""Tests for knowledge review API endpoints.

Uses a file-based test database to avoid FastAPI dependency override issues.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.common.knowledge.models import IngestedFile, KnowledgeChunk, KnowledgeDocument
from backend.core.db import Base, init_db


@pytest.fixture
def test_db_path():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_ai4law_")
    os.close(fd)
    yield Path(path)
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def db_session(test_db_path: Path):
    """Create a fresh test database with all tables."""
    db_url = f"sqlite:///{test_db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    init_db(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(test_db_path: Path, db_session: Session):
    """Build a FastAPI TestClient that uses the test database."""
    from backend.core.settings import get_settings

    # Clear cached settings so new env var takes effect
    get_settings.cache_clear()

    db_url = f"sqlite:///{test_db_path}"
    os.environ["AI4LAW_DATABASE_URL"] = db_url

    from backend.api.v1.endpoints.knowledge_review import router

    app = FastAPI()
    app.include_router(router, prefix="/knowledge/review")
    with TestClient(app) as test_client:
        yield test_client

    del os.environ["AI4LAW_DATABASE_URL"]
    get_settings.cache_clear()


def _seed_document(db: Session, **kwargs) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        title=kwargs.get("title", "测试法规"),
        doc_type=kwargs.get("doc_type", "law"),
        jurisdiction=kwargs.get("jurisdiction", "cn"),
        source=kwargs.get("source", "regulatory"),
        review_status=kwargs.get("review_status", "review_pending"),
        user_id=kwargs.get("user_id", ""),
    )
    db.add(doc)
    db.flush()
    db.commit()
    return doc


def _seed_chunk(db: Session, doc_id: int, **kwargs) -> KnowledgeChunk:
    chunk = KnowledgeChunk(
        chunk_id=kwargs.get("chunk_id", f"CN-LAW-{doc_id:03d}/AR1"),
        document_id=doc_id,
        article_no=kwargs.get("article_no", "1"),
        title=kwargs.get("title", "测试法规"),
        content=kwargs.get("content", "测试内容。"),
        structural_level=kwargs.get("structural_level", "article"),
        structural_path=kwargs.get("structural_path", "第一章/第一条"),
        review_status=kwargs.get("review_status", "review_pending"),
    )
    db.add(chunk)
    db.flush()
    db.commit()
    return chunk


class TestReviewQueue:
    def test_get_empty_queue(self, db_session: Session, client: TestClient) -> None:
        response = client.get("/knowledge/review/queue")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_queue_with_pending(self, db_session: Session, client: TestClient) -> None:
        _seed_document(db_session, title="个人信息保护法", review_status="review_pending")
        _seed_document(db_session, title="数据安全法", review_status="review_pending")
        _seed_document(db_session, title="已发布法规", review_status="published")

        response = client.get("/knowledge/review/queue?status=review_pending")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_get_queue_filtered_by_jurisdiction(self, db_session: Session, client: TestClient) -> None:
        _seed_document(db_session, title="中国法规", jurisdiction="cn")
        _seed_document(db_session, title="欧盟法规", jurisdiction="eu")

        response = client.get("/knowledge/review/queue?jurisdiction=cn")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_queue_filtered_by_source(self, db_session: Session, client: TestClient) -> None:
        _seed_document(db_session, title="法规库来源", source="regulatory")
        _seed_document(db_session, title="用户上传", source="user")

        response = client.get("/knowledge/review/queue?source=user")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_queue_includes_chunk_count(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR2")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR3")

        response = client.get("/knowledge/review/queue")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["chunk_count"] == 3


class TestReviewDocumentDetail:
    def test_get_document_detail(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规")

        response = client.get(f"/knowledge/review/queue/{doc.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "测试法规"

    def test_get_nonexistent_document(self, db_session: Session, client: TestClient) -> None:
        response = client.get("/knowledge/review/queue/99999")
        assert response.status_code == 404


class TestDocumentChunks:
    def test_get_document_chunks(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1", article_no="1")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR2", article_no="2")

        response = client.get(f"/knowledge/review/queue/{doc.id}/chunks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_chunks_nonexistent_document(self, db_session: Session, client: TestClient) -> None:
        response = client.get("/knowledge/review/queue/99999/chunks")
        assert response.status_code == 404


class TestUpdateChunk:
    def test_update_chunk_content(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规")
        chunk = _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1", content="原始内容")

        response = client.put(
            f"/knowledge/review/chunks/{chunk.id}",
            json={"content": "修改后的内容", "review_status": "reviewed"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "修改后的内容"

    def test_update_nonexistent_chunk(self, db_session: Session, client: TestClient) -> None:
        response = client.put("/knowledge/review/chunks/99999", json={"content": "新内容"})
        assert response.status_code == 404

    def test_partial_update_chunk(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规")
        chunk = _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1", article_no="1")

        response = client.put(f"/knowledge/review/chunks/{chunk.id}", json={"article_no": "39"})
        assert response.status_code == 200
        data = response.json()
        assert data["article_no"] == "39"


class TestApproveDocument:
    def test_approve_document(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规", review_status="review_pending")

        response = client.post(f"/knowledge/review/{doc.id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == doc.id
        assert data["status"] == "reviewed"

    def test_approve_nonexistent_document(self, db_session: Session, client: TestClient) -> None:
        response = client.post("/knowledge/review/99999/approve")
        assert response.status_code == 404


class TestPublishDocument:
    def test_publish_document(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规", review_status="reviewed")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1", article_no="1")

        response = client.post(f"/knowledge/review/{doc.id}/publish")
        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == doc.id
        assert data["status"] == "published"

    def test_publish_nonexistent_document(self, db_session: Session, client: TestClient) -> None:
        response = client.post("/knowledge/review/99999/publish")
        assert response.status_code == 404


class TestRejectDocument:
    def test_reject_document(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规", review_status="review_pending")

        response = client.post(f"/knowledge/review/{doc.id}/reject")
        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == doc.id
        assert data["status"] == "rejected"
