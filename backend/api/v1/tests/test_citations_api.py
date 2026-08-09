from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import create_app
from backend.core.settings import Settings
from backend.models.report import ReportArtifactModel
from backend.models.task import TaskOwnershipModel
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
        assert data["footnote_map"]["1"]["knowledge_url"] == "/evidence?source=CN-LAW-003&article=39"
        assert data["footnote_map"]["1"]["can_jump"] is True
        assert data["footnote_map"]["1"]["resolution"]["resolution_type"] == "exact_article"
        assert data["footnote_map"]["1"]["resolution"]["target_id"] == "CN-LAW-003:39"
        assert data["footnote_map"]["1"]["open_mode"] == "in_app"


def test_citation_report_does_not_synthesize_empty_footnote_map(tmp_path: Path, monkeypatch) -> None:
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
        assert data["citation_count"] == 0
        assert data["footnote_map"] == {}
        assert json.loads((output_dir / "citation_map.json").read_text(encoding="utf-8"))["footnote_map"] == {}


def test_citation_report_reads_registered_artifact_when_workspace_id_differs_from_output_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Recovered workspaces keep their own ID while artifacts retain the run output path."""
    task_id = "workspace-task-id"
    output_dir = tmp_path / "outputs" / "tia" / "run-output-id" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    citation_map_path = output_dir / "citation_map.json"
    citation_map_path.write_text(
        json.dumps(
            {
                "task_id": "run-output-id",
                "module": "tia",
                "footnote_map": {
                    "1": {
                        "citation_id": "CIT-EU-GDPR-ART46-P01",
                        "source_id": "EU-LAW-001",
                        "citation_type": "law_article",
                        "title": "GDPR (EU) 2016/679",
                        "article_no": "46",
                        "quote_text": "appropriate safeguards",
                    }
                },
                "all_items": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    with _owned_client(tmp_path, task_id) as (client, owner_token, _):
        session = client.app.state.container.session_factory()
        try:
            owner_id = session.execute(
                select(TaskOwnershipModel.user_id).where(TaskOwnershipModel.task_id == task_id)
            ).scalar_one()
            session.add(
                ReportArtifactModel(
                    user_id=owner_id,
                    owner_type="tia",
                    owner_id=task_id,
                    artifact_type="citation_map_json",
                    file_path=str(citation_map_path),
                )
            )
            session.commit()
        finally:
            session.close()

        response = client.get(
            f"/api/v1/citations/reports/{task_id}?module=tia",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert response.status_code == 200
        assert response.json()["citation_count"] == 1
        assert response.json()["footnote_map"]["1"]["article_no"] == "46"
