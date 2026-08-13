from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings
from backend.models.report import ReportArtifactModel
from backend.models.review import UploadedFileModel


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
    app = create_app(
        Settings(
            database_url=f"sqlite:///{db_path}",
            storage_dir=tmp_path / "storage",
        )
    )

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


def test_artifact_preview_rejects_other_users_registered_output_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_output_access.db'}",
            storage_dir=tmp_path / "storage",
        )
    )
    relative_path = Path("outputs/assessment/task-owner/outputs/report.md")
    absolute_path = tmp_path / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text("# 仅限所有者", encoding="utf-8")

    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "output-owner", "output-owner@test.local")
        other_token, _ = _register(client, "output-other", "output-other@test.local")
        session = app.state.container.session_factory()
        try:
            session.add(
                ReportArtifactModel(
                    id="artifact-output-owner",
                    user_id=owner_id,
                    owner_type="assessment",
                    owner_id="task-owner",
                    artifact_type="md",
                    file_path=str(absolute_path),
                    preview_json="{}",
                )
            )
            session.commit()
        finally:
            session.close()

        owner_response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(relative_path)},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert owner_response.status_code == 200

        other_response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(relative_path)},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert other_response.status_code == 403


def test_artifact_preview_rejects_unregistered_html_even_under_allowed_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_html_access.db'}",
            storage_dir=tmp_path / "storage",
        )
    )
    relative_path = Path("storage/reports/orphan/report.html")
    absolute_path = tmp_path / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text("<h1>未登记报告</h1>", encoding="utf-8")

    with TestClient(app) as client:
        token, _ = _register(client, "html-reader", "html-reader@test.local")
        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(relative_path)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


def test_artifact_endpoints_accept_owner_relative_path_through_storage_symlink(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release_dir = tmp_path / "release"
    runtime_storage = tmp_path / "runtime" / "storage"
    release_dir.mkdir()
    runtime_storage.mkdir(parents=True)
    (release_dir / "storage").symlink_to(runtime_storage, target_is_directory=True)
    monkeypatch.chdir(release_dir)

    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_symlink_access.db'}",
            storage_dir=Path("storage"),
        )
    )
    relative_path = Path("storage/reports/review/task-symlink/review_report.md")
    physical_path = runtime_storage / "reports/review/task-symlink/review_report.md"
    physical_path.parent.mkdir(parents=True)
    physical_path.write_text("# 符号链接报告\n\n所有者可访问。", encoding="utf-8")

    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "symlink-owner", "symlink-owner@test.local")
        other_token, _ = _register(client, "symlink-other", "symlink-other@test.local")
        session = app.state.container.session_factory()
        try:
            session.add(
                ReportArtifactModel(
                    id="artifact-symlink-owner",
                    user_id=owner_id,
                    owner_type="review",
                    owner_id="task-symlink",
                    artifact_type="md",
                    file_path=str(relative_path),
                    preview_json="{}",
                )
            )
            session.commit()
        finally:
            session.close()

        for endpoint in ("preview", "file", "download"):
            owner_response = client.get(
                f"/api/v1/artifacts/{endpoint}",
                params={"path": str(relative_path)},
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            assert owner_response.status_code == 200, endpoint

            other_response = client.get(
                f"/api/v1/artifacts/{endpoint}",
                params={"path": str(relative_path)},
                headers={"Authorization": f"Bearer {other_token}"},
            )
            assert other_response.status_code == 403, endpoint


def test_artifact_preview_accepts_owner_relative_path_through_outputs_symlink(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release_dir = tmp_path / "release"
    runtime_outputs = tmp_path / "runtime" / "outputs"
    release_dir.mkdir()
    runtime_outputs.mkdir(parents=True)
    (release_dir / "outputs").symlink_to(runtime_outputs, target_is_directory=True)
    monkeypatch.chdir(release_dir)

    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_outputs_symlink.db'}",
            storage_dir=release_dir / "storage",
        )
    )
    relative_path = Path("outputs/assessment/task-output/outputs/report.md")
    physical_path = runtime_outputs / "assessment/task-output/outputs/report.md"
    physical_path.parent.mkdir(parents=True)
    physical_path.write_text("# 输出报告", encoding="utf-8")

    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "output-symlink-owner", "output-symlink-owner@test.local")
        session = app.state.container.session_factory()
        try:
            session.add(
                ReportArtifactModel(
                    id="artifact-output-symlink",
                    user_id=owner_id,
                    owner_type="assessment",
                    owner_id="task-output",
                    artifact_type="md",
                    file_path=str(relative_path),
                    preview_json="{}",
                )
            )
            session.commit()
        finally:
            session.close()

        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(relative_path)},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert response.status_code == 200
    assert response.json()["file_name"] == "report.md"


def test_artifact_symlink_access_accepts_physical_request_but_still_requires_owner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release_dir = tmp_path / "release"
    runtime_storage = tmp_path / "runtime" / "storage"
    release_dir.mkdir()
    runtime_storage.mkdir(parents=True)
    (release_dir / "storage").symlink_to(runtime_storage, target_is_directory=True)
    monkeypatch.chdir(release_dir)
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_physical_request.db'}",
            storage_dir=Path("storage"),
        )
    )
    logical_path = Path("storage/uploads/task-upload/evidence.txt")
    physical_path = runtime_storage / "uploads/task-upload/evidence.txt"
    physical_path.parent.mkdir(parents=True)
    physical_path.write_text("owner evidence", encoding="utf-8")

    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "upload-owner", "upload-owner@test.local")
        other_token, _ = _register(client, "upload-other", "upload-other@test.local")
        session = app.state.container.session_factory()
        try:
            session.add(
                UploadedFileModel(
                    id="upload-symlink-owner",
                    user_id=owner_id,
                    task_id="task-upload",
                    filename="evidence.txt",
                    storage_path=str(logical_path),
                    extracted_text="owner evidence",
                )
            )
            session.commit()
        finally:
            session.close()

        owner_response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(physical_path)},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        other_response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(physical_path)},
            headers={"Authorization": f"Bearer {other_token}"},
        )

    assert owner_response.status_code == 200
    assert owner_response.json()["content"] == "owner evidence"
    assert other_response.status_code == 403


def test_artifact_symlink_access_rejects_unregistered_file(tmp_path: Path, monkeypatch) -> None:
    release_dir = tmp_path / "release"
    runtime_storage = tmp_path / "runtime" / "storage"
    release_dir.mkdir()
    runtime_storage.mkdir(parents=True)
    (release_dir / "storage").symlink_to(runtime_storage, target_is_directory=True)
    monkeypatch.chdir(release_dir)
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_unregistered_symlink.db'}",
            storage_dir=Path("storage"),
        )
    )
    orphan_path = runtime_storage / "reports/review/orphan/report.md"
    orphan_path.parent.mkdir(parents=True)
    orphan_path.write_text("not registered", encoding="utf-8")

    with TestClient(app) as client:
        token, _ = _register(client, "orphan-reader", "orphan-reader@test.local")
        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": "storage/reports/review/orphan/report.md"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


def test_artifact_symlink_access_rejects_file_outside_allowed_roots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release_dir = tmp_path / "release"
    runtime_storage = tmp_path / "runtime" / "storage"
    release_dir.mkdir()
    runtime_storage.mkdir(parents=True)
    (release_dir / "storage").symlink_to(runtime_storage, target_is_directory=True)
    monkeypatch.chdir(release_dir)
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_outside_root.db'}",
            storage_dir=Path("storage"),
        )
    )
    outside_path = tmp_path / "private.txt"
    outside_path.write_text("must stay private", encoding="utf-8")

    with TestClient(app) as client:
        token, _ = _register(client, "outside-reader", "outside-reader@test.local")
        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": str(outside_path)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Artifact path is outside allowed preview scope."


def test_artifact_symlink_access_returns_not_found_for_missing_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release_dir = tmp_path / "release"
    runtime_storage = tmp_path / "runtime" / "storage"
    release_dir.mkdir()
    runtime_storage.mkdir(parents=True)
    (release_dir / "storage").symlink_to(runtime_storage, target_is_directory=True)
    monkeypatch.chdir(release_dir)
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'artifact_missing_symlink.db'}",
            storage_dir=Path("storage"),
        )
    )

    with TestClient(app) as client:
        token, _ = _register(client, "missing-reader", "missing-reader@test.local")
        response = client.get(
            "/api/v1/artifacts/preview",
            params={"path": "storage/reports/missing/report.pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Artifact file not found."
