from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from backend.common.llm.client import LLMClient
from backend.common.llm.provider_registry import LLMProviderConfig, LLMProviderRegistry, normalize_openai_base_url

DEFAULT_LLM_MODELS = [
    "deepseek-ai/DeepSeek-V3.2",
    "deepseek-ai/DeepSeek-V3",
    "hy3-preview",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
]


def _builtin_provider_templates(settings) -> list[dict[str, Any]]:
    return [
        {
            "id": "siliconflow",
            "name": "SiliconFlow",
            "provider_type": "openai_compatible",
            "api_key": settings.siliconflow_api_key or "",
            "api_url": normalize_openai_base_url(settings.siliconflow_api_url),
            "model": settings.siliconflow_model,
            "enabled": bool(settings.siliconflow_api_key),
            "timeout": 60,
        },
        {
            "id": "tencent_hunyuan",
            "name": "Tencent Hunyuan",
            "provider_type": "openai_compatible",
            "api_key": settings.tencent_api_key or "",
            "api_url": normalize_openai_base_url(settings.tencent_api_url),
            "model": settings.tencent_model,
            "enabled": bool(settings.tencent_api_key),
            "timeout": 60,
        },
    ]


def _merge_builtin_providers(settings, providers: list[LLMProviderConfig]) -> list[LLMProviderConfig]:
    merged: dict[str, LLMProviderConfig] = {item.id: item for item in providers}
    for raw in _builtin_provider_templates(settings):
        if raw["id"] in merged:
            continue
        merged[raw["id"]] = LLMProviderConfig(
            id=raw["id"],
            name=raw["name"],
            provider_type=raw["provider_type"],
            api_url=raw["api_url"],
            api_key=raw["api_key"] or None,
            model=raw["model"],
            enabled=raw["enabled"],
            timeout=raw["timeout"],
        )
    return list(merged.values())


def _runtime_file_path(settings) -> Path:
    return settings.storage_dir / "runtime_settings.json"


def load_runtime_overrides(settings) -> dict[str, Any]:
    path = _runtime_file_path(settings)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_runtime_overrides(settings, payload: dict[str, Any]) -> None:
    path = _runtime_file_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_effective_runtime_payload(settings) -> dict[str, Any]:
    registry = LLMProviderRegistry(settings)
    providers = _merge_builtin_providers(settings, registry.list_providers())
    active = registry.get_active_provider(allow_disabled=True)
    base = {
        "delilegal": {
            "base_url": settings.delilegal_base_url,
            "app_id": settings.delilegal_app_id or "",
            "secret": "",
            "secret_configured": bool(settings.delilegal_secret),
        },
        "llm": {
            "active_provider_id": active.id,
            "providers": [
                {
                    **item.sanitized(),
                    "api_key": "",
                }
                for item in providers
            ],
            "provider": active.id,
            "api_key": "",
            "api_url": active.api_url,
            "model": active.model,
            "model_options": DEFAULT_LLM_MODELS,
        },
    }

    base["delilegal"]["enabled"] = bool(
        settings.delilegal_app_id and settings.delilegal_secret
    )
    base["llm"]["enabled"] = any(item.get("enabled") and item.get("api_key_configured") for item in base["llm"]["providers"])
    return base


def apply_runtime_payload(settings, payload: dict[str, Any]) -> dict[str, Any]:
    delilegal = payload.get("delilegal") if isinstance(payload.get("delilegal"), dict) else {}
    llm = payload.get("llm") if isinstance(payload.get("llm"), dict) else {}

    settings.delilegal_base_url = str(delilegal.get("base_url") or settings.delilegal_base_url).strip()
    settings.delilegal_app_id = str(delilegal.get("app_id") or "").strip() or None
    requested_delilegal_secret = str(delilegal.get("secret") or "").strip()
    if requested_delilegal_secret:
        settings.delilegal_secret = requested_delilegal_secret

    normalized_providers = _normalize_runtime_providers(
        settings,
        llm,
        payload.get("custom_providers"),
    )
    active_provider_id = _resolve_active_provider_id(llm, normalized_providers)
    _apply_active_provider_to_settings(settings, normalized_providers, active_provider_id)
    settings._runtime_llm_providers = normalized_providers
    settings._runtime_llm_active_provider_id = active_provider_id

    normalized = {
        "delilegal": {
            "base_url": settings.delilegal_base_url,
            "app_id": settings.delilegal_app_id or "",
            "secret": settings.delilegal_secret or "",
        },
        "llm": {
            "active_provider_id": active_provider_id,
            "providers": normalized_providers,
        },
    }
    save_runtime_overrides(settings, normalized)
    return build_effective_runtime_payload(settings)


def build_provider_test_result(
    provider_payload: dict[str, Any],
    settings=None,
) -> dict[str, Any]:
    if settings is not None:
        provider_payload = _with_preserved_provider_secret(
            settings,
            provider_payload,
        )
    provider = _normalize_single_provider(provider_payload)
    start = time.perf_counter()

    class _ProviderSettings:
        resolved_llm_provider = provider["id"]
        resolved_llm_model = provider["model"]
        resolved_llm_api_key = provider["api_key"] or None
        resolved_llm_api_url = provider["api_url"]
        _runtime_llm_providers = [provider]
        _runtime_llm_active_provider_id = provider["id"]

    client = LLMClient(_ProviderSettings())
    result = client.chat_with_metadata(
        system="You are a connectivity probe.",
        user="Reply with pong.",
        temperature=0,
        max_tokens=8,
        channel="settings_probe",
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    if result.get("fallback"):
        return {
            "ok": False,
            "provider_id": provider["id"],
            "provider_type": provider["provider_type"],
            "model": provider["model"],
            "latency_ms": latency_ms,
            "usage": result.get("usage") or {},
            "error": "Provider test failed",
        }
    return {
        "ok": True,
        "provider_id": provider["id"],
        "provider_type": provider["provider_type"],
        "model": provider["model"],
        "latency_ms": latency_ms,
        "usage": result.get("usage") or {},
        "error": "",
    }


def _with_preserved_provider_secret(
    settings,
    provider_payload: dict[str, Any],
) -> dict[str, Any]:
    candidate = dict(provider_payload)
    if str(candidate.get("api_key") or "").strip():
        return candidate

    provider_id = str(candidate.get("id") or "").strip()
    existing = next(
        (
            provider
            for provider in LLMProviderRegistry(settings).list_providers()
            if provider.id == provider_id
        ),
        None,
    )
    if existing and existing.api_key:
        candidate["api_key"] = existing.api_key
    return candidate


def _normalize_runtime_providers(
    settings,
    llm_payload: dict[str, Any],
    legacy_custom_providers: Any,
) -> list[dict[str, Any]]:
    providers = llm_payload.get("providers")
    if isinstance(providers, list) and providers:
        return [
            _normalize_single_provider(
                _with_preserved_provider_secret(settings, item)
            )
            for item in providers
            if isinstance(item, dict)
        ]

    legacy = []
    if isinstance(legacy_custom_providers, list):
        legacy.extend(item for item in legacy_custom_providers if isinstance(item, dict))
    legacy_provider_id = str(llm_payload.get("provider") or settings.resolved_llm_provider or "default").strip() or "default"
    legacy_default = {
        "id": legacy_provider_id,
        "name": legacy_provider_id,
        "provider_type": "openai_compatible",
        "api_key": str(llm_payload.get("api_key") or settings.resolved_llm_api_key or "").strip(),
        "api_url": str(llm_payload.get("api_url") or settings.resolved_llm_api_url or "").strip(),
        "model": str(llm_payload.get("model") or settings.resolved_llm_model or "").strip(),
        "enabled": bool(str(llm_payload.get("api_key") or settings.resolved_llm_api_key or "").strip()),
        "timeout": 60,
    }
    normalized = [_normalize_single_provider(legacy_default)]
    for item in legacy:
        try:
            normalized.append(_normalize_single_provider(item))
        except ValueError:
            continue
    return normalized


def _resolve_active_provider_id(llm_payload: dict[str, Any], providers: list[dict[str, Any]]) -> str:
    candidate = str(llm_payload.get("active_provider_id") or "").strip()
    if candidate and any(item["id"] == candidate for item in providers):
        return candidate
    if providers:
        return providers[0]["id"]
    raise ValueError("At least one provider is required")


def _apply_active_provider_to_settings(settings, providers: list[dict[str, Any]], active_provider_id: str) -> None:
    provider = next((item for item in providers if item["id"] == active_provider_id), None)
    if provider is None:
        raise ValueError(f"Active provider not found: {active_provider_id}")
    if not provider.get("enabled", True):
        raise ValueError(f"Active provider is disabled: {active_provider_id}")

    settings.llm_provider = str(provider["id"])
    settings.llm_api_key = str(provider.get("api_key") or "").strip() or None
    settings.llm_api_url = normalize_openai_base_url(str(provider.get("api_url") or "").strip())
    settings.llm_model = str(provider.get("model") or "").strip()


def _normalize_single_provider(item: dict[str, Any]) -> dict[str, Any]:
    provider = LLMProviderConfig(
        id=str(item.get("id") or "").strip(),
        name=str(item.get("name") or "").strip() or str(item.get("id") or "").strip(),
        provider_type=str(item.get("provider_type") or "openai_compatible").strip() or "openai_compatible",
        api_url=normalize_openai_base_url(str(item.get("api_url") or "").strip()),
        api_key=str(item.get("api_key") or "").strip() or None,
        model=str(item.get("model") or "").strip(),
        enabled=bool(item.get("enabled", True)),
        timeout=_normalize_timeout(item.get("timeout")),
    )
    if not provider.id:
        raise ValueError("Provider id is required")
    if not provider.name:
        raise ValueError("Provider name is required")
    if not provider.model:
        raise ValueError("Provider model is required")
    if provider.provider_type != "openai_compatible":
        raise ValueError(f"Unsupported provider type: {provider.provider_type}")
    return {
        "id": provider.id,
        "name": provider.name,
        "provider_type": provider.provider_type,
        "api_key": provider.api_key or "",
        "api_url": provider.api_url,
        "model": provider.model,
        "enabled": provider.enabled,
        "timeout": provider.timeout,
    }


def _normalize_timeout(value: Any) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = 60
    return max(1, timeout)
