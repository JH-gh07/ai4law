"""Tests for knowledge review API endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api import knowledge_review as kr
from backend.common.knowledge.models import IngestedFile, KnowledgeChunk, KnowledgeDocument
from backend.core.db import Base


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine) -> Session:
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def client(engine, db_session: Session) -> TestClient:
    app = FastAPI()

    def override_get_db():
        return db_session

    app.dependency_overrides[kr._get_db] = override_get_db
    app.include_router(kr.router, prefix="/knowledge/review")
    return TestClient(app)


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
    return chunk


class TestReviewQueue:
    def test_get_empty_queue(self, db_session: Session, client: TestClient) -> None:
        response = client.get("/knowledge/review/queue")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_get_queue_with_pending(self, db_session: Session, client: TestClient) -> None:
        _seed_document(db_session, title="个人信息保护法", review_status="review_pending")
        _seed_document(db_session, title="数据安全法", review_status="review_pending")
        _seed_document(db_session, title="已发布法规", review_status="published")

        response = client.get("/knowledge/review/queue?status=review_pending")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_queue_filtered_by_jurisdiction(self, db_session: Session, client: TestClient) -> None:
        _seed_document(db_session, title="中国法规", jurisdiction="cn", review_status="review_pending")
        _seed_document(db_session, title="欧盟法规", jurisdiction="eu", review_status="review_pending")

        response = client.get("/knowledge/review/queue?jurisdiction=cn")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "中国法规"

    def test_get_queue_filtered_by_doc_type(self, db_session: Session, client: TestClient) -> None:
        _seed_document(db_session, title="法律", doc_type="law", review_status="review_pending")
        _seed_document(db_session, title="标准", doc_type="standard", review_status="review_pending")

        response = client.get("/knowledge/review/queue?doc_type=law")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_queue_filtered_by_source(self, db_session: Session, client: TestClient) -> None:
        _seed_document(db_session, title="法规库来源", source="regulatory", review_status="review_pending")
        _seed_document(db_session, title="用户上传", source="user", review_status="review_pending")

        response = client.get("/knowledge/review/queue?source=user")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "用户上传"

    def test_get_queue_includes_chunk_count(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规", review_status="review_pending")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1", article_no="1")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR2", article_no="2")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR3", article_no="3")

        response = client.get("/knowledge/review/queue")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["chunk_count"] == 3


class TestReviewDocumentDetail:
    def test_get_document_detail(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规", review_status="review_pending")

        response = client.get(f"/knowledge/review/queue/{doc.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "测试法规"
        assert data["status"] == "review_pending"

    def test_get_nonexistent_document(self, db_session: Session, client: TestClient) -> None:
        response = client.get("/knowledge/review/queue/99999")
        assert response.status_code == 404


class TestDocumentChunks:
    def test_get_document_chunks(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1", article_no="1", content="第一条内容")
        _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR2", article_no="2", content="第二条内容")

        response = client.get(f"/knowledge/review/queue/{doc.id}/chunks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["article_no"] == "1"
        assert data[1]["article_no"] == "2"

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
        assert data["review_status"] == "reviewed"

    def test_update_nonexistent_chunk(self, db_session: Session, client: TestClient) -> None:
        response = client.put(
            "/knowledge/review/chunks/99999",
            json={"content": "新内容"},
        )
        assert response.status_code == 404

    def test_partial_update_chunk(self, db_session: Session, client: TestClient) -> None:
        doc = _seed_document(db_session, title="测试法规")
        chunk = _seed_chunk(db_session, doc.id, chunk_id="CN-LAW-001/AR1", article_no="1")

        response = client.put(
            f"/knowledge/review/chunks/{chunk.id}",
            json={"article_no": "39"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["article_no"] == "39"
        assert data["content"] == "测试内容。"  # unchanged


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
