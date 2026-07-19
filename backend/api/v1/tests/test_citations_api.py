from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.v1.endpoints.citations import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/citations")
    return TestClient(app)


def test_citation_report_supports_module_and_knowledge_url(tmp_path: Path, monkeypatch) -> None:
    task_id = "task-cite-1"
    output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "module": "assessment",
        "footnote_map": {
            "1": {
                "citation_id": "cit-1",
                "source_id": "CN-LAW-003",
                "citation_type": "law_article",
                "title": "个人信息保护法",
                "article_no": "39",
                "quote_text": "处理个人信息应当取得个人同意。",
            }
        },
        "all_items": [
            {
                "citation_id": "cit-1",
                "source_id": "CN-LAW-003",
                "citation_type": "law_article",
                "title": "个人信息保护法",
                "article_no": "39",
                "quote_text": "处理个人信息应当取得个人同意。",
            }
        ],
    }
    (output_dir / "citation_map.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    client = _client()
    response = client.get(f"/api/v1/citations/reports/{task_id}?module=assessment")
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "assessment"
    assert data["citation_count"] == 1
    assert data["footnote_map"]["1"]["knowledge_url"] == "/knowledge/laws/CN-LAW-003?article=39"
    assert data["footnote_map"]["1"]["can_jump"] is True


def test_citation_report_backfills_empty_footnote_map_from_outputs(tmp_path: Path, monkeypatch) -> None:
    task_id = "task-cite-2"
    output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "module": "assessment",
        "footnote_map": {},
        "all_items": [],
    }
    facts = {
        "regulations": [
            {
                "source_id": "CN-LAW-003",
                "title": "个人信息保护法",
                "article": "39",
                "snippet": "处理个人信息应当取得个人同意。",
            }
        ]
    }
    (output_dir / "citation_map.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (output_dir / "facts.json").write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    client = _client()
    response = client.get(f"/api/v1/citations/reports/{task_id}?module=assessment")
    assert response.status_code == 200
    data = response.json()
    assert data["citation_count"] == 1
    assert data["footnote_map"]["1"]["title"] == "个人信息保护法"
    assert data["footnote_map"]["1"]["article_no"] == "39"
