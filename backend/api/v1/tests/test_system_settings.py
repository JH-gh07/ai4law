from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.v1.endpoints import system_settings as system_settings_endpoint
from backend.app import create_app
from backend.core.dependencies import get_current_user
from backend.core.settings import Settings
from backend.schemas.auth import AuthUser


TEST_USER = AuthUser(
    id="settings-test-user",
    username="settings-test-user",
    email="settings-test@example.com",
)


def _settings_payload(api_key: str = "sk-demo") -> dict[str, object]:
    return {
        "delilegal": {
            "base_url": "https://openapi.delilegal.com",
            "app_id": "",
            "secret": "",
            "enabled": False,
        },
        "llm": {
            "active_provider_id": "deepseek-demo",
            "providers": [
                {
                    "id": "deepseek-demo",
                    "name": "DeepSeek Demo",
                    "provider_type": "openai_compatible",
                    "api_key": api_key,
                    "api_url": "https://api.deepseek.com/v1/chat/completions",
                    "model": "deepseek-chat",
                    "enabled": True,
                    "timeout": 30,
                }
            ],
            "model_options": [],
            "enabled": True,
        },
    }


@contextmanager
def _make_client(tmp_path: Path, *, authenticated: bool = True):
    db_path = tmp_path / "system_settings_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=tmp_path,
        _env_file=None,
    )
    app = create_app(settings)
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
    try:
        with TestClient(app) as client:
            yield client, settings
    finally:
        app.dependency_overrides.clear()


def test_runtime_settings_requires_authentication(tmp_path: Path) -> None:
    with _make_client(tmp_path, authenticated=False) as (client, _settings):
        assert client.get("/api/v1/system/settings/runtime").status_code == 401
        assert client.put(
            "/api/v1/system/settings/runtime",
            json=_settings_payload(),
        ).status_code == 401
        assert client.post(
            "/api/v1/system/settings/llm/test-provider",
            json={"provider": _settings_payload()["llm"]["providers"][0]},
        ).status_code == 401


def test_runtime_settings_returns_sanitized_provider_registry(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, _settings):
        response = client.get("/api/v1/system/settings/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert "active_provider_id" in payload["llm"]
    assert isinstance(payload["llm"]["providers"], list)
    assert payload["llm"]["providers"][0]["provider_type"] == "openai_compatible"
    assert payload["llm"]["api_key"] == ""
    assert payload["llm"]["providers"][0]["api_key"] == ""
    assert payload["delilegal"]["secret"] == ""


def test_runtime_settings_save_masks_provider_secret(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, settings):
        response = client.put(
            "/api/v1/system/settings/runtime",
            json=_settings_payload(),
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["llm"]["active_provider_id"] == "deepseek-demo"
        assert payload["llm"]["provider"] == "deepseek-demo"
        assert payload["llm"]["api_url"] == "https://api.deepseek.com/v1"
        assert payload["llm"]["providers"][0]["model"] == "deepseek-chat"
        assert payload["llm"]["providers"][0]["api_key"] == ""
        assert payload["llm"]["providers"][0]["api_key_configured"] is True
        assert settings._runtime_llm_providers[0]["api_key"] == "sk-demo"


def test_runtime_settings_blank_secret_preserves_existing_value(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, settings):
        first = client.put(
            "/api/v1/system/settings/runtime",
            json=_settings_payload("sk-existing"),
        )
        assert first.status_code == 200

        sanitized = first.json()
        second = client.put(
            "/api/v1/system/settings/runtime",
            json=sanitized,
        )

        assert second.status_code == 200
        assert second.json()["llm"]["providers"][0]["api_key"] == ""
        assert second.json()["llm"]["providers"][0]["api_key_configured"] is True
        assert settings._runtime_llm_providers[0]["api_key"] == "sk-existing"


def test_runtime_provider_test_endpoint_accepts_authenticated_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_result(provider_payload, settings):
        return {
            "ok": True,
            "provider_id": provider_payload["id"],
            "provider_type": provider_payload["provider_type"],
            "model": provider_payload["model"],
            "latency_ms": 1,
            "usage": {},
            "error": "",
        }

    monkeypatch.setattr(
        system_settings_endpoint,
        "build_provider_test_result",
        fake_result,
    )
    provider = _settings_payload()["llm"]["providers"][0]
    with _make_client(tmp_path) as (client, _settings):
        response = client.post(
            "/api/v1/system/settings/llm/test-provider",
            json={"provider": provider},
        )

    assert response.status_code == 200
    assert response.json()["provider_id"] == "deepseek-demo"
