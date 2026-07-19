from pathlib import Path

from contextlib import contextmanager

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings


@contextmanager
def _make_client(tmp_path: Path):
    db_path = tmp_path / "auth_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=tmp_path / "storage",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def test_auth_register_login_me_logout_flow(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        register = client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "alice-pass-123",
                "company_name": "Alice Co",
            },
        )
        assert register.status_code == 200
        payload = register.json()
        assert payload["access_token"]
        assert payload["user"]["username"] == "alice"

        token = payload["access_token"]

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "alice@example.com"

        logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout.status_code == 200

        me_after_logout = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_after_logout.status_code == 401


def test_auth_login_with_email_identifier(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "bob",
                "email": "bob@example.com",
                "password": "bob-pass-123",
            },
        )

        login = client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "bob@example.com",
                "password": "bob-pass-123",
                "remember": False,
            },
        )
        assert login.status_code == 200
        assert login.json()["user"]["username"] == "bob"


def test_auth_reject_duplicate_registration(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        first = client.post(
            "/api/v1/auth/register",
            json={
                "username": "same",
                "email": "same@example.com",
                "password": "same-pass-123",
            },
        )
        assert first.status_code == 200

        second = client.post(
            "/api/v1/auth/register",
            json={
                "username": "same",
                "email": "other@example.com",
                "password": "other-pass-123",
            },
        )
        assert second.status_code == 400
