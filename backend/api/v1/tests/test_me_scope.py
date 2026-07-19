from contextlib import contextmanager
from pathlib import Path
import json

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings
from backend.models.diagnosis import DiagnosisSessionModel
from backend.models.report import ReportArtifactModel
from backend.models.review import ReviewTaskModel, UploadedFileModel
from backend.models.workspace import WorkspaceStateModel


@contextmanager
def _make_client(tmp_path: Path):
    db_path = tmp_path / "me_scope_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=tmp_path / "storage",
    )
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


def test_workspace_recovery_reconstructs_run_and_response(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, app):
        token = _register(client, "carol", "carol@scope.test")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["user"]

        output_dir = tmp_path / "outputs" / "assessment" / "task-123" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "report.md").write_text("# 报告标题\n\n正文内容。", encoding="utf-8")
        (output_dir / "facts.json").write_text(
            json.dumps({"chapters": [{"title": "第一章", "content": "这里是正文"}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        session = app.state.container.session_factory()
        try:
            session.add(
                ReportArtifactModel(
                    id="report-r-1",
                    user_id=me["id"],
                    owner_type="assessment",
                    owner_id="task-123",
                    artifact_type="markdown",
                    file_path=str(output_dir / "report.md"),
                    preview_json='{"summary":"Recovered summary"}',
                )
            )
            session.commit()
        finally:
            session.close()

        response = client.get("/api/v1/me/workspace-recovery", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["task_id"] == "task-123"
        assert items[0]["run"]["async_task_id"] == "task-123"
        assert items[0]["run"]["response"]["chapters"][0]["title"] == "第一章"


def test_delete_project_history_removes_recovery_sources(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, app):
        token = _register(client, "dora", "dora@scope.test")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["user"]

        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        uploaded_file = upload_dir / "contract.docx"
        uploaded_file.write_text("demo", encoding="utf-8")

        output_dir = tmp_path / "outputs" / "review" / "task-delete-1" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        report_file = output_dir / "report.md"
        report_file.write_text("# Report", encoding="utf-8")

        stored_report_dir = tmp_path / "storage" / "reports" / "review" / "task-delete-1"
        stored_report_dir.mkdir(parents=True, exist_ok=True)
        html_file = stored_report_dir / "report.html"
        html_file.write_text("<h1>Report</h1>", encoding="utf-8")

        session = app.state.container.session_factory()
        try:
            session.add(ReviewTaskModel(id="task-delete-1", user_id=me["id"], status="COMPLETED", progress=100))
            session.add(
                UploadedFileModel(
                    id="upload-1",
                    user_id=me["id"],
                    task_id="task-delete-1",
                    filename="contract.docx",
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    storage_path=str(uploaded_file),
                    extracted_text="demo",
                )
            )
            session.add(
                ReportArtifactModel(
                    id="report-delete-1",
                    user_id=me["id"],
                    owner_type="review",
                    owner_id="task-delete-1",
                    artifact_type="markdown",
                    file_path=str(report_file),
                    preview_json='{"summary":"Delete me"}',
                )
            )
            session.add(
                ReportArtifactModel(
                    id="report-delete-2",
                    user_id=me["id"],
                    owner_type="review",
                    owner_id="task-delete-1",
                    artifact_type="html",
                    file_path=str(html_file),
                    preview_json='{"summary":"Delete me too"}',
                )
            )
            session.add(
                WorkspaceStateModel(
                    user_id=me["id"],
                    state_json=json.dumps(
                        {
                            "task_spaces": [{"id": "task-delete-1", "name": "Delete Target"}],
                            "module_runs": [{"id": "run-1", "taskSpaceId": "task-delete-1"}],
                            "artifacts": [{"id": "art-1", "taskSpaceId": "task-delete-1"}],
                            "evidence_hits": [{"id": "hit-1", "taskSpaceId": "task-delete-1"}],
                            "issues": [{"id": "issue-1", "taskSpaceId": "task-delete-1"}],
                        },
                        ensure_ascii=False,
                    ),
                )
            )
            session.commit()
        finally:
            session.close()

        delete_response = client.delete("/api/v1/me/projects/task-delete-1", headers={"Authorization": f"Bearer {token}"})
        assert delete_response.status_code == 200
        delete_payload = delete_response.json()
        assert delete_payload["task_id"] == "task-delete-1"
        assert delete_payload["deleted_review_tasks"] == 1
        assert delete_payload["deleted_uploaded_files"] == 1
        assert delete_payload["deleted_report_records"] == 2
        assert delete_payload["deleted_task_spaces"] == 1
        assert delete_payload["deleted_module_runs"] == 1
        assert delete_payload["deleted_artifacts"] == 1
        assert delete_payload["deleted_evidence_hits"] == 1
        assert delete_payload["deleted_issues"] == 1

        tasks = client.get("/api/v1/me/tasks", headers={"Authorization": f"Bearer {token}"})
        assert tasks.status_code == 200
        assert tasks.json()["items"] == []

        reports = client.get("/api/v1/me/reports", headers={"Authorization": f"Bearer {token}"})
        assert reports.status_code == 200
        assert reports.json()["items"] == []

        recovery = client.get("/api/v1/me/workspace-recovery", headers={"Authorization": f"Bearer {token}"})
        assert recovery.status_code == 200
        assert recovery.json()["items"] == []

        workspace_state = client.get("/api/v1/workspace-state", headers={"Authorization": f"Bearer {token}"})
        assert workspace_state.status_code == 200
        state = workspace_state.json()["state"]
        assert state["task_spaces"] == []
        assert state["module_runs"] == []
        assert state["artifacts"] == []
        assert state["evidence_hits"] == []
        assert state["issues"] == []

        assert not uploaded_file.exists()
        assert not report_file.exists()
        assert not html_file.exists()
        assert not output_dir.parent.exists()
        assert not stored_report_dir.exists()
