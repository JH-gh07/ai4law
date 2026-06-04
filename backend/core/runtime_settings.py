from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from backend.common.llm.client import LLMClient
from backend.common.llm.provider_registry import LLMProviderConfig, LLMProviderRegistry, normalize_openai_base_url
from backend.services.legal_api_service import DeliLegalService

DELILEGAL_COMPETITION_APP_ID = "QthdBErlyaYvyXul"
DELILEGAL_COMPETITION_SECRET = "EC5D455E6BD348CE8E18BE05926D2EBE"

DEFAULT_LLM_MODELS = [
    "hunyuan-lite",
    "hunyuan-turbos-latest",
    "hunyuan-standard",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "deepseek-ai/DeepSeek-V3",
]


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
    providers = registry.list_providers()
    active = registry.get_active_provider(allow_disabled=True)
    base = {
        "delilegal": {
            "base_url": settings.delilegal_base_url,
            "app_id": settings.delilegal_app_id or DELILEGAL_COMPETITION_APP_ID,
            "secret": settings.delilegal_secret or DELILEGAL_COMPETITION_SECRET,
        },
        "llm": {
            "active_provider_id": active.id,
            "providers": [
                {
                    **item.sanitized(),
                    "api_key": item.api_key or "",
                }
                for item in providers
            ],
            "provider": active.id,
            "api_key": active.api_key or "",
            "api_url": active.api_url,
            "model": active.model,
            "model_options": DEFAULT_LLM_MODELS,
        },
    }

    overrides = load_runtime_overrides(settings)
    for section in ("delilegal",):
        if isinstance(overrides.get(section), dict):
            base[section].update(overrides[section])

    base["delilegal"]["enabled"] = bool(base["delilegal"].get("app_id") and base["delilegal"].get("secret"))
    base["llm"]["enabled"] = any(item.get("enabled") and item.get("api_key_configured") for item in base["llm"]["providers"])
    return base


def apply_runtime_payload(settings, payload: dict[str, Any]) -> dict[str, Any]:
    delilegal = payload.get("delilegal") if isinstance(payload.get("delilegal"), dict) else {}
    llm = payload.get("llm") if isinstance(payload.get("llm"), dict) else {}

    settings.delilegal_base_url = str(delilegal.get("base_url") or settings.delilegal_base_url).strip()
    settings.delilegal_app_id = str(delilegal.get("app_id") or "").strip() or None
    settings.delilegal_secret = str(delilegal.get("secret") or "").strip() or None

    normalized_providers = _normalize_runtime_providers(settings, llm, payload.get("custom_providers"))
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


def refresh_runtime_clients(container) -> None:
    container.llm_client = LLMClient(container.settings)
    container.legal_api_service = DeliLegalService(container.settings)

    container.diagnosis_service.llm_client = container.llm_client
    container.diagnosis_service.legal_api_service = container.legal_api_service

    container.review_service.knowledge_base.legal_api_service = container.legal_api_service
    container.review_service.reviewer.llm_client = container.llm_client

    from backend.common.rag import retriever as rag_retriever

    rag_retriever._service.cache_clear()
    rag_retriever._default_legal_service = container.legal_api_service
    rag_retriever._default_legal_service_loaded = True

    from backend.modules.assessment.router import service as assessment_service
    from backend.modules.bcr.router import service as bcr_service
    from backend.modules.cn_flow.router import service as cn_flow_service
    from backend.modules.cpra.router import service as cpra_service
    from backend.modules.diagnosis.router import renderer as diagnosis_renderer
    from backend.modules.dpia.router import service as dpia_service
    from backend.modules.pipia.router import service as pipia_service
    from backend.modules.scc.router import service as scc_service
    from backend.modules.tia.router import service as tia_service
    from backend.modules.v0_task_gateway.router import service as v0_gateway_service

    assessment_service.generator.llm = container.llm_client
    assessment_service.retriever.legal_service = container.legal_api_service

    scc_service.llm_client = container.llm_client
    pipia_service.llm_client = container.llm_client
    bcr_service.llm_client = container.llm_client
    dpia_service.llm_client = container.llm_client
    tia_service.llm_client = container.llm_client
    cn_flow_service.llm_client = container.llm_client
    cpra_service.llm_client = container.llm_client
    diagnosis_renderer.llm_client = container.llm_client

    v0_gateway_service.assessment.generator.llm = container.llm_client
    v0_gateway_service.assessment.retriever.legal_service = container.legal_api_service
    v0_gateway_service.pipia.llm_client = container.llm_client
    v0_gateway_service.bcr.llm_client = container.llm_client
    v0_gateway_service.dpia.llm_client = container.llm_client
    v0_gateway_service.tia.llm_client = container.llm_client
    v0_gateway_service.cn_flow.llm_client = container.llm_client
    v0_gateway_service.cpra.llm_client = container.llm_client


def build_provider_test_result(provider_payload: dict[str, Any]) -> dict[str, Any]:
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


def _normalize_runtime_providers(settings, llm_payload: dict[str, Any], legacy_custom_providers: Any) -> list[dict[str, Any]]:
    providers = llm_payload.get("providers")
    if isinstance(providers, list) and providers:
        return [_normalize_single_provider(item) for item in providers if isinstance(item, dict)]

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
