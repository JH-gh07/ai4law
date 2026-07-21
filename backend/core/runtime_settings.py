from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from backend.common.llm.client import LLMClient
from backend.common.llm.provider_registry import LLMProviderConfig, LLMProviderRegistry, normalize_openai_base_url
from backend.integrations.delilegal import DeliLegalService
from backend.services.runtime_health import record_llm_health

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

    def finish(result: dict[str, Any]) -> dict[str, Any]:
        if settings is not None:
            record_llm_health(settings, provider, result)
        return result

    discovery = client.discover_models()
    discovery_status = str(discovery.get("status") or "unsupported_or_failed")
    available_models = [str(item) for item in discovery.get("models") or []]
    if discovery_status == "available" and provider["model"] not in available_models:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return finish({
            "ok": False,
            "provider_id": provider["id"],
            "provider_type": provider["provider_type"],
            "model": provider["model"],
            "latency_ms": latency_ms,
            "usage": {},
            "error_code": "MODEL_NOT_FOUND",
            "error_category": "model",
            "error": f"模型 {provider['model']} 不在 Provider 返回的可用模型列表中",
            "model_discovery": discovery_status,
            "available_models": available_models[:100],
        })
    result = client.chat_with_metadata(
        system="You are a connectivity probe.",
        user="Reply with pong.",
        temperature=0,
        max_tokens=8,
        channel="settings_probe",
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    if result.get("fallback"):
        error_code, error_category, error_message = _classify_provider_probe_error(
            str(result.get("error") or ""),
            str(result.get("error_type") or ""),
        )
        return finish({
            "ok": False,
            "provider_id": provider["id"],
            "provider_type": provider["provider_type"],
            "model": provider["model"],
            "latency_ms": latency_ms,
            "usage": result.get("usage") or {},
            "error_code": error_code,
            "error_category": error_category,
            "error": error_message,
            "model_discovery": discovery_status,
            "available_models": available_models[:100],
        })
    return finish({
        "ok": True,
        "provider_id": provider["id"],
        "provider_type": provider["provider_type"],
        "model": provider["model"],
        "latency_ms": latency_ms,
        "usage": result.get("usage") or {},
        "error_code": "",
        "error_category": "",
        "error": "",
        "model_discovery": discovery_status,
        "available_models": available_models[:100],
    })


def build_delilegal_test_result(
    config_payload: dict[str, Any],
    settings,
) -> dict[str, Any]:
    requested_secret = str(config_payload.get("secret") or "").strip()

    class _DeliSettings:
        delilegal_base_url = str(
            config_payload.get("base_url") or settings.delilegal_base_url
        ).strip()
        delilegal_app_id = str(config_payload.get("app_id") or "").strip() or None
        delilegal_secret = requested_secret or settings.delilegal_secret

    service = DeliLegalService(_DeliSettings())
    result = service.probe()
    return {
        **result,
        "base_url": service.base_url,
    }


def _classify_provider_probe_error(
    error: str,
    error_type: str = "",
) -> tuple[str, str, str]:
    text = f"{error_type} {error}".strip().lower()
    patterns = [
        (
            ("模型下线", "已下线", "retired", "decommissioned", "no longer available"),
            ("MODEL_RETIRED", "model", "模型已下线或不再提供，请选择 Provider 当前支持的模型"),
        ),
        (
            ("余额不足", "额度不足", "insufficient_quota", "insufficient quota", "credit balance", "quota exceeded"),
            ("INSUFFICIENT_QUOTA", "quota", "Provider 额度或余额不足，请充值、调整额度或更换 Provider"),
        ),
        (
            ("模型不存在", "model_not_found", "model not found", "does not exist"),
            ("MODEL_NOT_FOUND", "model", "配置的模型不存在，请先执行模型发现并选择可用模型"),
        ),
        (
            ("invalid api key", "incorrect api key", "unauthorized", "authentication", "鉴权失败", "密钥无效", " 401"),
            ("AUTHENTICATION_FAILED", "authentication", "Provider 鉴权失败，请检查 API Key、App ID 和访问权限"),
        ),
        (
            ("api key is not configured", "notconfigured"),
            ("NOT_CONFIGURED", "configuration", "Provider 未配置 API Key，无法执行真实模型探测"),
        ),
        (
            ("rate limit", "ratelimiterror", "too many requests", " 429"),
            ("RATE_LIMITED", "rate_limit", "Provider 请求过于频繁，请稍后重试或调整限流配置"),
        ),
        (
            ("timeout", "timed out", "超时"),
            ("TIMEOUT", "network", "Provider 请求超时，请检查网络、Base URL 或超时设置"),
        ),
        (
            ("connection", "connecterror", "dns", "ssl", "network"),
            ("NETWORK_ERROR", "network", "无法连接 Provider，请检查 Base URL、DNS、TLS 和网络策略"),
        ),
    ]
    for needles, classification in patterns:
        if any(needle in text for needle in needles):
            return classification
    return "PROVIDER_ERROR", "provider", "Provider 最小生成探测失败，请检查 Provider 返回的错误日志"


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
