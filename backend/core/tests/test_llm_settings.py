from __future__ import annotations

import pytest

from backend.common.llm.client import LLMClient
from backend.core.runtime_settings import (
    apply_runtime_payload,
    build_effective_runtime_payload,
    build_provider_test_result,
)
from backend.core.settings import Settings


_LLM_ENV_KEYS = [
    "LLM_PROVIDER",
    "AI4LAW_LLM_PROVIDER",
    "LLM_API_KEY",
    "AI4LAW_LLM_API_KEY",
    "LLM_API_URL",
    "AI4LAW_LLM_API_URL",
    "LLM_MODEL",
    "AI4LAW_LLM_MODEL",
    "TENCENT_API_KEY",
    "AI4LAW_TENCENT_API_KEY",
    "TENCENT_API_URL",
    "AI4LAW_TENCENT_API_URL",
    "TENCENT_MODEL",
    "AI4LAW_TENCENT_MODEL",
    "SILICONFLOW_API_KEY",
    "SICICONFLOW_API_KEY",
    "AI4LAW_SILICONFLOW_API_KEY",
    "AI4LAW_SICICONFLOW_API_KEY",
    "SILICONFLOW_API_URL",
    "SICICONFLOW_API_URL",
    "AI4LAW_SILICONFLOW_API_URL",
    "AI4LAW_SICICONFLOW_API_URL",
    "SILICONFLOW_MODEL",
    "SICICONFLOW_MODEL",
    "AI4LAW_SILICONFLOW_MODEL",
    "AI4LAW_SICICONFLOW_MODEL",
]


def _clear_llm_env(monkeypatch) -> None:
    for key in _LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_schema_first_assessment_flag_is_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED", raising=False)
    assert Settings(_env_file=None).schema_first_assessment_enabled is False

    monkeypatch.setenv("AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED", "true")
    assert Settings(_env_file=None).schema_first_assessment_enabled is True


def test_settings_accepts_siciconflow_typo_env_aliases(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("SICICONFLOW_API_KEY", "sf-test-key")
    monkeypatch.setenv("SICICONFLOW_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
    monkeypatch.setenv("SICICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3.2")

    settings = Settings(_env_file=None)

    assert settings.resolved_llm_provider == "siliconflow"
    assert settings.resolved_llm_api_key == "sf-test-key"
    assert settings.resolved_llm_api_url == "https://api.siliconflow.cn/v1"
    assert settings.resolved_llm_model == "deepseek-ai/DeepSeek-V3.2"


def test_llm_client_uses_resolved_siliconflow_config(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("SILICONFLOW_API_KEY", "sf-test-key")
    monkeypatch.setenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3.2")

    client = LLMClient(Settings(_env_file=None))

    assert client._provider == "siliconflow"
    assert client._api_key == "sf-test-key"
    assert client._api_url == "https://api.siliconflow.cn/v1"
    assert client._model == "deepseek-ai/DeepSeek-V3.2"


def test_llm_client_without_provider_credentials_uses_fallback(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)

    client = LLMClient(Settings(_env_file=None))
    result = client.chat_with_metadata(system="system", user="user")

    assert client.enabled is False
    assert client._provider == "none"
    assert result["fallback"] is True


def test_runtime_settings_can_apply_siliconflow_provider(tmp_path) -> None:
    settings = Settings(storage_dir=tmp_path, _env_file=None)

    payload = apply_runtime_payload(
        settings,
        {
            "llm": {
                "provider": "siliconflow",
                "api_key": "runtime-sf-key",
                "api_url": "https://api.siliconflow.cn/v1/chat/completions",
                "model": "Qwen/Qwen2.5-7B-Instruct",
            }
        },
    )

    assert payload["llm"]["provider"] == "siliconflow"
    assert payload["llm"]["api_key"] == ""
    assert payload["llm"]["api_url"] == "https://api.siliconflow.cn/v1"
    assert payload["llm"]["model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert payload["llm"]["providers"][0]["api_key"] == ""
    assert payload["llm"]["providers"][0]["api_key_configured"] is True
    assert build_effective_runtime_payload(settings)["llm"]["enabled"] is True


@pytest.mark.parametrize(
    "api_key",
    [
        "valid-prefix\nexport TENCENT_API_URL=https://example.com",
        "valid-prefix\rmalicious",
        "valid-prefix\x00malicious",
    ],
)
def test_runtime_settings_rejects_shell_contaminated_api_keys(
    tmp_path,
    api_key,
) -> None:
    settings = Settings(storage_dir=tmp_path, _env_file=None)

    with pytest.raises(ValueError, match="API key contains invalid characters"):
        apply_runtime_payload(
            settings,
            {
                "llm": {
                    "active_provider_id": "contaminated",
                    "providers": [
                        {
                            "id": "contaminated",
                            "name": "Contaminated",
                            "provider_type": "openai_compatible",
                            "api_key": api_key,
                            "api_url": "https://example.com/v1",
                            "model": "example-model",
                            "enabled": True,
                        }
                    ],
                }
            },
        )


def test_settings_use_tencent_defaults_when_tencent_provider_is_active(monkeypatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "tencent_hunyuan")
    monkeypatch.setenv("TENCENT_API_KEY", "tx-test-key")

    settings = Settings(_env_file=None)

    assert settings.resolved_llm_provider == "tencent_hunyuan"
    assert settings.resolved_llm_api_key == "tx-test-key"
    assert settings.resolved_llm_api_url == "https://tokenhub.tencentmaas.com/v1"
    assert settings.resolved_llm_model == "hy3-preview"

def test_delilegal_has_no_embedded_competition_credentials(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AI4LAW_DELILEGAL_APP_ID", raising=False)
    monkeypatch.delenv("AI4LAW_DELILEGAL_SECRET", raising=False)

    settings = Settings(storage_dir=tmp_path, _env_file=None)
    payload = build_effective_runtime_payload(settings)

    assert payload["delilegal"]["app_id"] == ""
    assert payload["delilegal"]["secret"] == ""
    assert payload["delilegal"]["enabled"] is False


def test_runtime_settings_mask_and_preserve_existing_secrets(
    tmp_path,
    monkeypatch,
) -> None:
    _clear_llm_env(monkeypatch)
    settings = Settings(storage_dir=tmp_path, _env_file=None)

    first = apply_runtime_payload(
        settings,
        {
            "delilegal": {
                "base_url": "https://openapi.delilegal.com",
                "app_id": "demo-app",
                "secret": "deli-secret",
            },
            "llm": {
                "active_provider_id": "demo",
                "providers": [
                    {
                        "id": "demo",
                        "name": "Demo",
                        "provider_type": "openai_compatible",
                        "api_key": "llm-secret",
                        "api_url": "https://example.com/v1",
                        "model": "demo-model",
                        "enabled": True,
                        "timeout": 30,
                    }
                ],
            },
        },
    )

    assert first["delilegal"]["secret"] == ""
    assert first["delilegal"]["secret_configured"] is True
    assert first["llm"]["providers"][0]["api_key"] == ""
    assert first["llm"]["providers"][0]["api_key_configured"] is True

    second = apply_runtime_payload(settings, first)

    assert settings.delilegal_secret == "deli-secret"
    assert settings._runtime_llm_providers[0]["api_key"] == "llm-secret"
    assert second["delilegal"]["secret_configured"] is True
    assert second["llm"]["providers"][0]["api_key_configured"] is True


def test_provider_probe_reuses_existing_secret_when_request_is_masked(
    tmp_path,
    monkeypatch,
) -> None:
    settings = Settings(storage_dir=tmp_path, _env_file=None)
    apply_runtime_payload(
        settings,
        {
            "llm": {
                "active_provider_id": "demo",
                "providers": [
                    {
                        "id": "demo",
                        "name": "Demo",
                        "provider_type": "openai_compatible",
                        "api_key": "probe-secret",
                        "api_url": "https://example.com/v1",
                        "model": "demo-model",
                        "enabled": True,
                        "timeout": 30,
                    }
                ],
            },
        },
    )
    observed = {}

    def fake_chat(client, **_kwargs):
        observed["api_key"] = client._api_key
        return {"fallback": False, "usage": {}}

    monkeypatch.setattr(
        LLMClient,
        "discover_models",
        lambda _client: {
            "status": "unsupported_or_failed",
            "models": [],
            "error": "models endpoint unavailable",
        },
    )
    monkeypatch.setattr(LLMClient, "chat_with_metadata", fake_chat)
    result = build_provider_test_result(
        {
            "id": "demo",
            "name": "Demo",
            "provider_type": "openai_compatible",
            "api_key": "",
            "api_url": "https://example.com/v1",
            "model": "demo-model",
            "enabled": True,
            "timeout": 30,
        },
        settings,
    )

    assert result["ok"] is True
    assert observed["api_key"] == "probe-secret"


def test_provider_probe_rejects_model_missing_from_discovered_models(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        LLMClient,
        "discover_models",
        lambda _client: {
            "status": "available",
            "models": ["available-model"],
            "error": "",
        },
        raising=False,
    )

    def unexpected_chat(*_args, **_kwargs):
        raise AssertionError("minimal generation must not run for a missing model")

    monkeypatch.setattr(LLMClient, "chat_with_metadata", unexpected_chat)
    result = build_provider_test_result(
        {
            "id": "demo",
            "name": "Demo",
            "provider_type": "openai_compatible",
            "api_key": "probe-secret",
            "api_url": "https://example.com/v1",
            "model": "missing-model",
            "enabled": True,
            "timeout": 30,
        },
    )

    assert result["ok"] is False
    assert result["error_code"] == "MODEL_NOT_FOUND"
    assert result["error_category"] == "model"
    assert result["model_discovery"] == "available"


def test_provider_probe_classifies_insufficient_quota(monkeypatch) -> None:
    monkeypatch.setattr(
        LLMClient,
        "discover_models",
        lambda _client: {
            "status": "unsupported_or_failed",
            "models": [],
            "error": "models endpoint unavailable",
        },
    )
    monkeypatch.setattr(
        LLMClient,
        "chat_with_metadata",
        lambda _client, **_kwargs: {
            "fallback": True,
            "usage": {"usage_source": "unavailable"},
            "error": "Error code: 429 - 账户余额不足",
            "error_type": "RateLimitError",
        },
    )

    result = build_provider_test_result(
        {
            "id": "demo",
            "name": "Demo",
            "provider_type": "openai_compatible",
            "api_key": "probe-secret",
            "api_url": "https://example.com/v1",
            "model": "demo-model",
            "enabled": True,
            "timeout": 30,
        },
    )

    assert result["ok"] is False
    assert result["error_code"] == "INSUFFICIENT_QUOTA"
    assert result["error_category"] == "quota"
    assert "余额" in result["error"]


def test_provider_probe_distinguishes_actionable_failure_categories(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        LLMClient,
        "discover_models",
        lambda _client: {
            "status": "unsupported_or_failed",
            "models": [],
            "error": "models endpoint unavailable",
        },
    )
    current_error = {"message": ""}
    monkeypatch.setattr(
        LLMClient,
        "chat_with_metadata",
        lambda _client, **_kwargs: {
            "fallback": True,
            "usage": {"usage_source": "unavailable"},
            "error": current_error["message"],
            "error_type": "APIError",
        },
    )
    provider = {
        "id": "demo",
        "name": "Demo",
        "provider_type": "openai_compatible",
        "api_key": "probe-secret",
        "api_url": "https://example.com/v1",
        "model": "demo-model",
        "enabled": True,
        "timeout": 30,
    }
    cases = {
        "该模型已下线": ("MODEL_RETIRED", "model"),
        "model does not exist": ("MODEL_NOT_FOUND", "model"),
        "invalid API key": ("AUTHENTICATION_FAILED", "authentication"),
        "rate limit exceeded": ("RATE_LIMITED", "rate_limit"),
        "request timed out": ("TIMEOUT", "network"),
        "connection refused": ("NETWORK_ERROR", "network"),
        "unclassified provider rejection": ("PROVIDER_ERROR", "provider"),
    }

    for error_message, expected in cases.items():
        current_error["message"] = error_message
        result = build_provider_test_result(provider)
        assert (result["error_code"], result["error_category"]) == expected
