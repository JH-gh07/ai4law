from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from fastapi import HTTPException, Request

from backend.common.llm.provider_registry import LLMProviderRegistry


HEALTH_TTL_SECONDS = 15 * 60


def provider_fingerprint(provider: Any) -> str:
    def value(name: str, default: Any = "") -> Any:
        if isinstance(provider, dict):
            return provider.get(name, default)
        return getattr(provider, name, default)

    key_digest = hashlib.sha256(
        str(value("api_key") or "").encode("utf-8")
    ).hexdigest()
    payload = {
        "id": str(value("id") or ""),
        "provider_type": str(value("provider_type") or ""),
        "api_url": str(value("api_url") or "").rstrip("/"),
        "model": str(value("model") or ""),
        "enabled": bool(value("enabled", True)),
        "api_key_digest": key_digest,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def record_llm_health(settings: Any, provider: Any, result: dict[str, Any]) -> None:
    provider_id = (
        str(provider.get("id") or "")
        if isinstance(provider, dict)
        else str(getattr(provider, "id", "") or "")
    )
    settings._runtime_provider_health[provider_id] = {
        "ok": bool(result.get("ok")),
        "checked_at_epoch": time.time(),
        "fingerprint": provider_fingerprint(provider),
        "error_code": str(result.get("error_code") or ""),
        "error": str(result.get("error") or ""),
    }


def require_healthy_llm(request: Request) -> None:
    settings = request.app.state.container.settings
    if str(settings.app_env or "").strip().lower() != "production":
        return

    provider = LLMProviderRegistry(settings).get_active_provider(
        allow_disabled=True
    )
    snapshot = settings._runtime_provider_health.get(provider.id)
    reason = "Provider 尚未通过健康探测"
    if not provider.enabled or not provider.api_key_configured:
        reason = "Provider 未启用或未配置 API Key"
    elif snapshot is None:
        reason = "Provider 尚未通过健康探测"
    elif snapshot.get("fingerprint") != provider_fingerprint(provider):
        reason = "Provider 配置已变更，需要重新探测"
    elif time.time() - float(snapshot.get("checked_at_epoch") or 0) > HEALTH_TTL_SECONDS:
        reason = "Provider 健康探测已过期，需要重新探测"
    elif snapshot.get("ok") is True:
        return
    else:
        reason = str(snapshot.get("error") or reason)

    raise HTTPException(
        status_code=503,
        detail={
            "code": "LLM_PROVIDER_UNHEALTHY",
            "provider_id": provider.id,
            "model": provider.model,
            "reason": reason,
            "action": "请在设置页测试当前 Provider，并在通过后重新启动任务",
        },
    )
