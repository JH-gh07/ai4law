from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings
from backend.models.report import ReportArtifactModel


def _register(client: TestClient, username: str, email: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "pass-12345678",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    return payload["access_token"], payload["user"]["id"]


def test_artifact_preview_accepts_relative_report_path_for_owner(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "artifact_access_test.db"
    app = create_app(Settings(database_url=f"sqlite:///{db_path}"))

    relative_report_path = Path("storage/reports/review/task-1/review_report.md")
    absolute_report_path = tmp_path / relative_report_path
    absolute_report_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_report_path.write_text("# 审查报告\n\n内容正常。", encoding="utf-8")

    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "artifact-owner", "artifact-owner@test.local")
        other_token, _ = _register(client, "artifact-other", "artifact-other@test.local")

        session = app.state.container.session_factory()
        try:
            session.add(
                ReportArtifactModel(
                    id="artifact-report-1",
                    user_id=owner_id,
                    owner_type="review",
                    owner_id="task-1",
                    artifact_type="md",
                    file_path=str(relative_report_path),
                    preview_json="{}",
                )
            )
            session.commit()
        finally:
            session.close()

        owner_preview = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(relative_report_path)},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert owner_preview.status_code == 200
        assert owner_preview.json()["file_name"] == "review_report.md"
        assert "内容正常" in owner_preview.json()["content"]

        other_preview = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(relative_report_path)},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert other_preview.status_code == 403
