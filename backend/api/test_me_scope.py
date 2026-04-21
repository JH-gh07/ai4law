from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings
from backend.models.diagnosis import DiagnosisSessionModel
from backend.models.report import ReportArtifactModel
from backend.models.review import ReviewTaskModel


@contextmanager
def _make_client(tmp_path: Path):
    db_path = tmp_path / "me_scope_test.db"
    settings = Settings(database_url=f"sqlite:///{db_path}")
    app = create_app(settings)
    with TestClient(app) as client:
        yield client, app


def _register(client: TestClient, username: str, email: str) -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "pass-12345678",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_my_data_endpoints_are_user_scoped(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, app):
        token_a = _register(client, "alice", "alice@scope.test")
        token_b = _register(client, "bob", "bob@scope.test")

        me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()["user"]
        me_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()["user"]

        session = app.state.container.session_factory()
        try:
            session.add(
                DiagnosisSessionModel(
                    id="diag-a-1",
                    user_id=me_a["id"],
                    status="COMPLETED",
                    answers_json="{}",
                    result_json="{}",
                    context_json="{}",
                )
            )
            session.add(
                DiagnosisSessionModel(
                    id="diag-b-1",
                    user_id=me_b["id"],
                    status="COMPLETED",
                    answers_json="{}",
                    result_json="{}",
                    context_json="{}",
                )
            )
            session.add(ReviewTaskModel(id="review-a-1", user_id=me_a["id"], status="COMPLETED", progress=100))
            session.add(ReviewTaskModel(id="review-b-1", user_id=me_b["id"], status="FAILED", progress=20))
            session.add(
                ReportArtifactModel(
                    id="report-a-1",
                    user_id=me_a["id"],
                    owner_type="diagnosis",
                    owner_id="diag-a-1",
                    artifact_type="html",
                    file_path="/tmp/a.html",
                    preview_json='{"summary":"A summary","risk_level":"MEDIUM"}',
                )
            )
            session.add(
                ReportArtifactModel(
                    id="report-b-1",
                    user_id=me_b["id"],
                    owner_type="diagnosis",
                    owner_id="diag-b-1",
                    artifact_type="html",
                    file_path="/tmp/b.html",
                    preview_json='{"summary":"B summary","risk_level":"HIGH"}',
                )
            )
            session.commit()
        finally:
            session.close()

        tasks_a = client.get("/api/v1/me/tasks", headers={"Authorization": f"Bearer {token_a}"})
        assert tasks_a.status_code == 200
        ids_a = {item["id"] for item in tasks_a.json()["items"]}
        assert "diag-a-1" in ids_a
        assert "review-a-1" in ids_a
        assert "diag-b-1" not in ids_a
        assert "review-b-1" not in ids_a

        tasks_b = client.get("/api/v1/me/tasks", headers={"Authorization": f"Bearer {token_b}"})
        assert tasks_b.status_code == 200
        ids_b = {item["id"] for item in tasks_b.json()["items"]}
        assert "diag-b-1" in ids_b
        assert "review-b-1" in ids_b
        assert "diag-a-1" not in ids_b

        reports_a = client.get("/api/v1/me/reports", headers={"Authorization": f"Bearer {token_a}"})
        assert reports_a.status_code == 200
        report_ids_a = {item["id"] for item in reports_a.json()["items"]}
        assert "report-a-1" in report_ids_a
        assert "report-b-1" not in report_ids_a

        meta_a = client.get("/api/v1/reports/diag-a-1/metadata", headers={"Authorization": f"Bearer {token_a}"})
        assert meta_a.status_code == 200
        assert meta_a.json()["summary"] == "A summary"

        meta_b = client.get("/api/v1/reports/diag-a-1/metadata", headers={"Authorization": f"Bearer {token_b}"})
        assert meta_b.status_code == 200
        assert meta_b.json()["summary"] is None
