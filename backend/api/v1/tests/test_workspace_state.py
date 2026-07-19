from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings


@contextmanager
def _make_client(tmp_path: Path):
    db_path = tmp_path / "workspace_state_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=tmp_path / "storage",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


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


def test_workspace_state_is_user_scoped(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        token_a = _register(client, "usera", "a@ws.test")
        token_b = _register(client, "userb", "b@ws.test")

        put_a = client.put(
            "/api/v1/workspace-state",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "task_spaces": [{"id": "task-a-1", "name": "A"}],
                "module_runs": [{"id": "run-a-1"}],
                "artifacts": [{"id": "artifact-a-1"}],
                "evidence_hits": [{"id": "ev-a-1"}],
                "issues": [{"id": "issue-a-1"}],
            },
        )
        assert put_a.status_code == 200

        put_b = client.put(
            "/api/v1/workspace-state",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "task_spaces": [{"id": "task-b-1", "name": "B"}],
                "module_runs": [],
                "artifacts": [],
                "evidence_hits": [],
                "issues": [],
            },
        )
        assert put_b.status_code == 200

        get_a = client.get("/api/v1/workspace-state", headers={"Authorization": f"Bearer {token_a}"})
        assert get_a.status_code == 200
        assert get_a.json()["state"]["task_spaces"][0]["id"] == "task-a-1"

        get_b = client.get("/api/v1/workspace-state", headers={"Authorization": f"Bearer {token_b}"})
        assert get_b.status_code == 200
        assert get_b.json()["state"]["task_spaces"][0]["id"] == "task-b-1"
