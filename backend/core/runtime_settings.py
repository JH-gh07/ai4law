from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.common.llm.client import LLMClient
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
    base = {
        "delilegal": {
            "base_url": settings.delilegal_base_url,
            "app_id": settings.delilegal_app_id or DELILEGAL_COMPETITION_APP_ID,
            "secret": settings.delilegal_secret or DELILEGAL_COMPETITION_SECRET,
        },
        "llm": {
            "provider": settings.resolved_llm_provider,
            "api_key": settings.resolved_llm_api_key or "",
            "api_url": settings.resolved_llm_api_url,
            "model": settings.resolved_llm_model,
            "model_options": DEFAULT_LLM_MODELS,
        },
        "custom_providers": [],
    }

    overrides = load_runtime_overrides(settings)
    for section in ("delilegal", "llm"):
        if isinstance(overrides.get(section), dict):
            base[section].update(overrides[section])

    providers = overrides.get("custom_providers")
    if isinstance(providers, list):
        base["custom_providers"] = [item for item in providers if isinstance(item, dict)]

    base["delilegal"]["enabled"] = bool(base["delilegal"].get("app_id") and base["delilegal"].get("secret"))
    base["llm"]["enabled"] = bool(base["llm"].get("api_key"))
    return base


def apply_runtime_payload(settings, payload: dict[str, Any]) -> dict[str, Any]:
    delilegal = payload.get("delilegal") if isinstance(payload.get("delilegal"), dict) else {}
    llm = payload.get("llm") if isinstance(payload.get("llm"), dict) else {}

    settings.delilegal_base_url = str(delilegal.get("base_url") or settings.delilegal_base_url).strip()
    settings.delilegal_app_id = str(delilegal.get("app_id") or "").strip() or None
    settings.delilegal_secret = str(delilegal.get("secret") or "").strip() or None

    provider = str(llm.get("provider") or settings.resolved_llm_provider).strip() or "auto"
    api_key = str(llm.get("api_key") or "").strip() or None
    api_url = str(llm.get("api_url") or "").strip()
    model = str(llm.get("model") or "").strip()

    settings.llm_provider = provider
    if provider == "siliconflow":
        settings.siliconflow_api_key = api_key
        if api_url:
            settings.siliconflow_api_url = api_url
        if model:
            settings.siliconflow_model = model
    elif provider in {"tencent", "tencent_hunyuan"}:
        settings.tencent_api_key = api_key
        if api_url:
            settings.tencent_api_url = api_url
        if model:
            settings.llm_model = model
    else:
        settings.llm_api_key = api_key
        if api_url:
            settings.llm_api_url = api_url
        if model:
            settings.llm_model = model

    normalized = {
        "delilegal": {
            "base_url": settings.delilegal_base_url,
            "app_id": settings.delilegal_app_id or "",
            "secret": settings.delilegal_secret or "",
        },
        "llm": {
            "provider": settings.resolved_llm_provider,
            "api_key": settings.resolved_llm_api_key or "",
            "api_url": settings.resolved_llm_api_url,
            "model": settings.resolved_llm_model,
        },
        "custom_providers": payload.get("custom_providers", []),
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
