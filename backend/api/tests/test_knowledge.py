from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.knowledge import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/knowledge")
    return TestClient(app)


def test_knowledge_index_returns_user_facing_filters() -> None:
    client = _client()
    response = client.get("/api/v1/knowledge/index")
    assert response.status_code == 200
    payload = response.json()
    assert "source_options" in payload
    assert "categories" in payload["source_options"]
    assert "jurisdictions" in payload["source_options"]
    assert "usages" in payload["source_options"]
    assert "scenarios" in payload["case_options"]
    first_source = payload["sources"][0]
    assert "category" in first_source
    assert "usage" in first_source
    assert "report_usage" in first_source


def test_knowledge_search_uses_unified_article_index() -> None:
    client = _client()
    response = client.get("/api/v1/knowledge/search", params={"q": "个人信息保护法 第三十九条", "jurisdiction": "cn"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["hit_count"] >= 1
    assert any("个人信息保护法" in item["title"] for item in payload["items"])


def test_article_detail_accepts_chinese_article_reference() -> None:
    client = _client()
    response = client.get("/api/v1/knowledge/sources/CN-LAW-003/articles/第三十九条")
    assert response.status_code == 200
    payload = response.json()
    assert payload["article_no"] == "39"
    assert payload["article_content"]
