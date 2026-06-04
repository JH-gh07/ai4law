from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings


@contextmanager
def _make_client(tmp_path: Path):
    db_path = tmp_path / "system_settings_test.db"
    settings = Settings(database_url=f"sqlite:///{db_path}")
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def test_runtime_settings_returns_provider_registry_shape(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.get("/api/v1/system/settings/runtime")
        assert response.status_code == 200
        payload = response.json()
        assert "llm" in payload
        assert "active_provider_id" in payload["llm"]
        assert isinstance(payload["llm"]["providers"], list)
        assert payload["llm"]["providers"][0]["provider_type"] == "openai_compatible"


def test_runtime_settings_can_save_active_provider_registry(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.put(
            "/api/v1/system/settings/runtime",
            json={
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
                            "api_key": "sk-demo",
                            "api_url": "https://api.deepseek.com/v1/chat/completions",
                            "model": "deepseek-chat",
                            "enabled": True,
                            "timeout": 30,
                            "api_key_configured": True,
                        }
                    ],
                    "model_options": [],
                    "enabled": True,
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["llm"]["active_provider_id"] == "deepseek-demo"
        assert payload["llm"]["provider"] == "deepseek-demo"
        assert payload["llm"]["api_url"] == "https://api.deepseek.com/v1"
        assert payload["llm"]["providers"][0]["model"] == "deepseek-chat"


def test_runtime_provider_test_endpoint_accepts_openai_compatible_provider(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.post(
            "/api/v1/system/settings/llm/test-provider",
            json={
                "provider": {
                    "id": "probe-openai",
                    "name": "Probe OpenAI Compat",
                    "provider_type": "openai_compatible",
                    "api_key": "test-key",
                    "api_url": "https://example.com/v1/chat/completions",
                    "model": "demo-model",
                    "enabled": True,
                    "timeout": 5,
                    "api_key_configured": True,
                }
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["provider_id"] == "probe-openai"
        assert payload["provider_type"] == "openai_compatible"
        assert payload["model"] == "demo-model"

