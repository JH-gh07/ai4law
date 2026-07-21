from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings


@pytest.fixture
def authenticated_client(tmp_path: Path) -> Iterator[TestClient]:
    """Create an isolated application client with one authenticated test user."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'api_test.db'}",
        storage_dir=tmp_path / "storage",
        _env_file=None,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "async-test-user",
                "email": "async-test@example.com",
                "password": "async-test-password",
            },
        )
        assert response.status_code == 200
        client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        yield client
