"""Task067 T04 — controlled report_ir access over the artifact preview API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.common.reporting import (
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    Provenance,
    ReportMetadata,
    SectionIR,
)
from backend.core.settings import Settings
from backend.models.report import ReportArtifactModel


def _register(client: TestClient, username: str, email: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "pass-12345678"},
    )
    assert response.status_code == 200
    payload = response.json()
    return payload["access_token"], payload["user"]["id"]


def _minimal_ir_dict() -> dict:
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="bcr",
        metadata=ReportMetadata(title="测试报告", company_name="TestCo"),
        provenance=Provenance(generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc)),
        findings=[
            FindingRecord(
                finding_id="F-1", requirement_id="R-1", title="约束力不足",
                risk_level="HIGH", statement="现状不合规。",
            )
        ],
        sections=[
            SectionIR(section_id="s1", title="详细 finding", level=1, blocks=[
                FindingDetailBlock(block_id="b1", finding_ref="F-1"),
            ]),
        ],
    )
    return document.model_dump(mode="json")


def _add_artifact(session, *, user_id: str, path: str, artifact_type: str) -> None:
    session.add(
        ReportArtifactModel(
            id=f"ir-{artifact_type}-{user_id[:6]}",
            user_id=user_id,
            owner_type="bcr",
            owner_id="task-1",
            artifact_type=artifact_type,
            file_path=path,
            preview_json="{}",
        )
    )
    session.commit()


def test_owner_reads_valid_document_ir_as_report_ir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(Settings(
        database_url=f"sqlite:///{tmp_path / 'ir_owner.db'}",
        storage_dir=tmp_path / "storage",
    ))
    rel = Path("outputs/bcr/task-1/outputs/document_ir.json")
    abs_path = tmp_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(json.dumps(_minimal_ir_dict(), ensure_ascii=False), encoding="utf-8")

    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "ir-owner", "ir-owner@test.local")
        session = app.state.container.session_factory()
        try:
            _add_artifact(session, user_id=owner_id, path=str(rel), artifact_type="document_ir_json")
        finally:
            session.close()

        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(rel)},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["render_mode"] == "report_ir"
    assert body["kind"] == "document_ir_json"
    # structured content must not leak into raw-text content
    assert body["content"] == ""
    assert body["report_ir"]["document_id"] == "doc-1"
    assert body["report_ir"]["findings"][0]["finding_id"] == "F-1"


def test_other_user_cannot_read_document_ir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(Settings(
        database_url=f"sqlite:///{tmp_path / 'ir_other.db'}",
        storage_dir=tmp_path / "storage",
    ))
    rel = Path("outputs/bcr/task-1/outputs/document_ir.json")
    abs_path = tmp_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(json.dumps(_minimal_ir_dict()), encoding="utf-8")

    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "ir-owner2", "ir-owner2@test.local")
        other_token, _ = _register(client, "ir-other2", "ir-other2@test.local")
        session = app.state.container.session_factory()
        try:
            _add_artifact(session, user_id=owner_id, path=str(rel), artifact_type="document_ir_json")
        finally:
            session.close()

        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(rel)},
            headers={"Authorization": f"Bearer {other_token}"},
        )

    assert response.status_code == 403


def test_arbitrary_json_is_not_treated_as_report_ir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(Settings(
        database_url=f"sqlite:///{tmp_path / 'ir_plain_json.db'}",
        storage_dir=tmp_path / "storage",
    ))
    rel = Path("outputs/bcr/task-1/outputs/summary.json")
    abs_path = tmp_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text('{"note": "not an IR"}', encoding="utf-8")

    with TestClient(app) as client:
        token, user_id = _register(client, "ir-json", "ir-json@test.local")
        session = app.state.container.session_factory()
        try:
            _add_artifact(session, user_id=user_id, path=str(rel), artifact_type="json")
        finally:
            session.close()

        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(rel)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["render_mode"] == "text"
    assert body["report_ir"] is None
    assert "not an IR" in body["content"]


def test_corrupted_document_ir_returns_422(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(Settings(
        database_url=f"sqlite:///{tmp_path / 'ir_corrupt.db'}",
        storage_dir=tmp_path / "storage",
    ))
    rel = Path("outputs/bcr/task-1/outputs/document_ir.json")
    abs_path = tmp_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text("{ not valid json", encoding="utf-8")

    with TestClient(app) as client:
        token, user_id = _register(client, "ir-corrupt", "ir-corrupt@test.local")
        session = app.state.container.session_factory()
        try:
            _add_artifact(session, user_id=user_id, path=str(rel), artifact_type="document_ir_json")
        finally:
            session.close()

        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(rel)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422
    assert "Corrupted document IR" in response.json()["detail"]


def test_unknown_schema_version_returns_422(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(Settings(
        database_url=f"sqlite:///{tmp_path / 'ir_version.db'}",
        storage_dir=tmp_path / "storage",
    ))
    rel = Path("outputs/bcr/task-1/outputs/document_ir.json")
    abs_path = tmp_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _minimal_ir_dict()
    payload["schema_version"] = "99.0"
    abs_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with TestClient(app) as client:
        token, user_id = _register(client, "ir-version", "ir-version@test.local")
        session = app.state.container.session_factory()
        try:
            _add_artifact(session, user_id=user_id, path=str(rel), artifact_type="document_ir_json")
        finally:
            session.close()

        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(rel)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422
    assert "Unknown DocumentIR schema version" in response.json()["detail"]


def test_v3_document_ir_is_migrated_to_v4(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(Settings(
        database_url=f"sqlite:///{tmp_path / 'ir_v3.db'}",
        storage_dir=tmp_path / "storage",
    ))
    rel = Path("outputs/bcr/task-1/outputs/document_ir.json")
    abs_path = tmp_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    v3_payload = {
        "schema_version": "3.0",
        "document_id": "doc-v3",
        "report_type": "bcr",
        "metadata": {"title": "v3 报告", "company_name": "V3Co"},
        "provenance": {"generated_at": "2026-08-08T00:00:00Z"},
        "sections": [
            {
                "section_id": "s1",
                "title": "正文",
                "level": 1,
                "blocks": [{"block_id": "b1", "type": "paragraph", "text": "内容"}],
            }
        ],
        "compiler_version": "0.0.1",
        "prompt_version": "v3",
        "template_version": "v3",
        "model": "legacy",
    }
    abs_path.write_text(json.dumps(v3_payload, ensure_ascii=False), encoding="utf-8")

    with TestClient(app) as client:
        token, user_id = _register(client, "ir-v3", "ir-v3@test.local")
        session = app.state.container.session_factory()
        try:
            _add_artifact(session, user_id=user_id, path=str(rel), artifact_type="document_ir_json")
        finally:
            session.close()

        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(rel)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["render_mode"] == "report_ir"
    assert body["report_ir"]["schema_version"] == "4.0"
    assert body["report_ir"]["migrated_from_schema"] == "3.0"
