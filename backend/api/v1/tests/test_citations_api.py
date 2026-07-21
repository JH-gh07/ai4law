from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings
from backend.services.task_access import claim_task_access


def _register(client: TestClient, username: str, email: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "pass-12345678"},
    )
    assert response.status_code == 200
    payload = response.json()
    return payload["access_token"], payload["user"]["id"]


@contextmanager
def _owned_client(tmp_path: Path, task_id: str):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'citation_access.db'}",
            storage_dir=tmp_path / "storage",
        )
    )
    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "citation-owner", "citation-owner@test.local")
        other_token, _ = _register(client, "citation-other", "citation-other@test.local")
        session = app.state.container.session_factory()
        try:
            claim_task_access(
                session,
                task_id=task_id,
                user_id=owner_id,
                module="assessment",
            )
        finally:
            session.close()
        yield client, owner_token, other_token


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
    with _owned_client(tmp_path, task_id) as (client, owner_token, other_token):
        unauthenticated = client.get(f"/api/v1/citations/reports/{task_id}?module=assessment")
        assert unauthenticated.status_code == 401

        forbidden = client.get(
            f"/api/v1/citations/reports/{task_id}?module=assessment",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert forbidden.status_code == 404

        response = client.get(
            f"/api/v1/citations/reports/{task_id}?module=assessment",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "assessment"
        assert data["citation_count"] == 1
        assert data["footnote_map"]["1"]["knowledge_url"] == "/knowledge/laws/CN-LAW-003?article=39"
        assert data["footnote_map"]["1"]["can_jump"] is True
        assert data["footnote_map"]["1"]["resolution"]["resolution_type"] == "exact_article"
        assert data["footnote_map"]["1"]["resolution"]["target_id"] == "CN-LAW-003:39"
        assert data["footnote_map"]["1"]["open_mode"] == "in_app"


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
    with _owned_client(tmp_path, task_id) as (client, owner_token, _):
        response = client.get(
            f"/api/v1/citations/reports/{task_id}?module=assessment",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["citation_count"] == 1
        assert data["footnote_map"]["1"]["title"] == "个人信息保护法"
        assert data["footnote_map"]["1"]["article_no"] == "39"
