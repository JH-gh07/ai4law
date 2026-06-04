from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_PROVIDER_TYPES = {"openai_compatible"}


@dataclass
class LLMProviderConfig:
    id: str
    name: str
    provider_type: str
    api_url: str
    api_key: str | None
    model: str
    enabled: bool = True
    timeout: int = 60

    @property
    def api_key_configured(self) -> bool:
        return bool((self.api_key or "").strip())

    def sanitized(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider_type": self.provider_type,
            "api_url": self.api_url,
            "model": self.model,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "api_key_configured": self.api_key_configured,
        }


def normalize_openai_base_url(url: str) -> str:
    normalized = (url or "").strip().rstrip("/")
    suffix = "/chat/completions"
    if normalized.endswith(suffix):
        normalized = normalized[: -len(suffix)]
    return normalized


class LLMProviderRegistry:
    def __init__(self, settings) -> None:
        self.settings = settings

    def list_providers(self) -> list[LLMProviderConfig]:
        providers = getattr(self.settings, "_runtime_llm_providers", None)
        if isinstance(providers, list) and providers:
            return [self._coerce_provider(item) for item in providers]
        return [self._build_legacy_default_provider()]

    def get_active_provider(self, *, allow_disabled: bool = False) -> LLMProviderConfig:
        providers = self.list_providers()
        active_id = str(getattr(self.settings, "_runtime_llm_active_provider_id", "") or "").strip()
        if not active_id and providers:
            active_id = providers[0].id

        provider = next((item for item in providers if item.id == active_id), None)
        if provider is None:
            raise ValueError(f"Active provider not found: {active_id}")
        if not allow_disabled and not provider.enabled:
            raise ValueError(f"Active provider is disabled: {active_id}")
        if provider.provider_type not in SUPPORTED_PROVIDER_TYPES:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")
        return provider

    def sanitize_provider(self, provider: LLMProviderConfig) -> dict[str, Any]:
        return provider.sanitized()

    def _coerce_provider(self, item: Any) -> LLMProviderConfig:
        raw = item if isinstance(item, dict) else {}
        provider_type = str(raw.get("provider_type") or "openai_compatible").strip() or "openai_compatible"
        return LLMProviderConfig(
            id=str(raw.get("id") or "").strip(),
            name=str(raw.get("name") or "").strip(),
            provider_type=provider_type,
            api_url=normalize_openai_base_url(str(raw.get("api_url") or "").strip()),
            api_key=str(raw.get("api_key") or "").strip() or None,
            model=str(raw.get("model") or "").strip(),
            enabled=bool(raw.get("enabled", True)),
            timeout=self._normalize_timeout(raw.get("timeout")),
        )

    def _build_legacy_default_provider(self) -> LLMProviderConfig:
        provider = str(self.settings.resolved_llm_provider or "default").strip() or "default"
        return LLMProviderConfig(
            id=provider,
            name=provider,
            provider_type="openai_compatible",
            api_url=normalize_openai_base_url(self.settings.resolved_llm_api_url),
            api_key=self.settings.resolved_llm_api_key,
            model=self.settings.resolved_llm_model,
            enabled=bool(self.settings.resolved_llm_api_key),
            timeout=60,
        )

    @staticmethod
    def _normalize_timeout(value: Any) -> int:
        try:
            timeout = int(value)
        except (TypeError, ValueError):
            timeout = 60
        return max(1, timeout)
