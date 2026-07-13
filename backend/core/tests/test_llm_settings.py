from __future__ import annotations

from backend.common.llm.client import LLMClient
from backend.core.runtime_settings import apply_runtime_payload, build_effective_runtime_payload
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
    assert payload["llm"]["api_key"] == "runtime-sf-key"
    assert payload["llm"]["api_url"] == "https://api.siliconflow.cn/v1"
    assert payload["llm"]["model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert payload["llm"]["providers"][0]["api_key"] == "runtime-sf-key"
    assert payload["llm"]["providers"][0]["api_key_configured"] is True
    assert build_effective_runtime_payload(settings)["llm"]["enabled"] is True


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
