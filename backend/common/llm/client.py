from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from backend.common.llm.provider_registry import LLMProviderRegistry
from backend.common.llm.context import current_llm_client
from backend.common.llm.snapshot import ProviderSnapshot
from backend.common.trace.context import current_trace

try:
    from openai import OpenAI, APIError
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]

    class APIError(Exception):
        pass

if TYPE_CHECKING:
    from backend.core.settings import Settings

logger = logging.getLogger(__name__)

_FALLBACK_MESSAGE = "（LLM服务暂时不可用，请稍后重试）"


@dataclass
class LLMUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    usage_source: str = "unavailable"

    def as_dict(self) -> dict[str, int | str]:
        payload: dict[str, int | str] = {"usage_source": self.usage_source}
        if self.prompt_tokens is not None:
            payload["prompt_tokens"] = self.prompt_tokens
        if self.completion_tokens is not None:
            payload["completion_tokens"] = self.completion_tokens
        if self.total_tokens is not None:
            payload["total_tokens"] = self.total_tokens
        return payload


class LLMClient:
    """OpenAI-compatible LLM client.

    用法::

        client = LLMClient(settings)
        text = client.chat(
            system="你是一名中国数据合规律师",
            user="请分析以下条款的合规风险...",
        )
    """

    def __init__(self, settings: Settings) -> None:
        # Routers construct some services before create_app() applies runtime
        # provider overrides. Keep the client disabled until that refresh runs.
        provider = LLMProviderRegistry(settings).get_active_provider(allow_disabled=True)
        self._provider_id = provider.id
        self._provider_name = provider.name
        self._provider_type = provider.provider_type
        self._provider = provider.id
        self._model = provider.model
        self._api_key = provider.api_key
        self._api_url = provider.api_url
        self._timeout = provider.timeout
        self._provider_enabled = provider.enabled
        self._client: Any | None = None
        self._client_init_error: str | None = None
        self._enabled = provider.enabled and bool(self._api_key) and OpenAI is not None
        if OpenAI is None:
            logger.warning("LLMClient: openai package not installed, falling back to placeholder outputs.")
        logger.info(
            "LLMClient initialized: provider_id=%s provider_name=%s provider_type=%s model=%s base_url=%s api_key_configured=%s",
            self._provider_id,
            self._provider_name,
            self._provider_type,
            self._model,
            self._api_url,
            bool(self._api_key),
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def provider_snapshot(self) -> ProviderSnapshot:
        return ProviderSnapshot(
            provider_id=self._provider_id,
            provider_name=self._provider_name,
            provider_type=self._provider_type,
            api_url=self._api_url,
            model=self._model,
            enabled=self._provider_enabled,
            timeout=self._timeout,
            api_key=self._api_key,
        )

    @classmethod
    def from_provider_snapshot(cls, snapshot: ProviderSnapshot) -> "LLMClient":
        client = cls.__new__(cls)
        client._provider_id = snapshot.provider_id
        client._provider_name = snapshot.provider_name
        client._provider_type = snapshot.provider_type
        client._provider = snapshot.provider_id
        client._model = snapshot.model
        client._api_key = snapshot.api_key
        client._api_url = snapshot.api_url
        client._timeout = snapshot.timeout
        client._provider_enabled = snapshot.enabled
        client._client = None
        client._client_init_error = None
        client._enabled = (
            snapshot.enabled and bool(snapshot.api_key) and OpenAI is not None
        )
        return client

    def clone(self) -> "LLMClient":
        return self.from_provider_snapshot(self.provider_snapshot())

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        channel: str = "workflow",
    ) -> str:
        return self.chat_with_metadata(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            channel=channel,
        )["content"]

    def chat_with_metadata(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        channel: str = "workflow",
    ) -> dict[str, object]:
        """发送一轮对话，返回模型回复文本。

        如果 API 未配置或调用失败，返回降级占位文本（不抛异常）。
        """
        from backend.common.tasks.cancellation import TaskCancelled, raise_if_task_cancelled

        raise_if_task_cancelled()
        scoped_client = current_llm_client.get()
        if scoped_client is not None and scoped_client is not self:
            return scoped_client.chat_with_metadata(
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                channel=channel,
            )

        trace = current_trace.get()
        if trace is not None:
            trace.record(
                "tool_start",
                {
                    "summary": "请求模型生成",
                    "detail": {
                        "tool": "llm_chat",
                        "channel": channel,
                        "provider": self._provider,
                        "provider_id": self._provider_id,
                        "provider_name": self._provider_name,
                        "provider_type": self._provider_type,
                        "base_url": self._api_url,
                        "model": self._model,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "llm": {
                            "channel": channel,
                            "provider": self._provider,
                            "model": self._model,
                        },
                        "system": system[:400],
                        "user": user[:800],
                        "raw_name": "llm_chat_request",
                    },
                },
            )

        if not self._enabled:
            logger.warning("LLMClient: API key not configured for provider %s, returning fallback text.", self._provider)
            return self._fallback_metadata(
                trace=trace,
                channel=channel,
                error="API key is not configured",
                error_type="NotConfigured",
            )

        client = self._ensure_client()
        if client is None:
            logger.warning(
                "LLMClient: provider %s client unavailable (%s), returning fallback text.",
                self._provider_id,
                self._client_init_error or "unknown_error",
            )
            return self._fallback_metadata(
                trace=trace,
                channel=channel,
                error=self._client_init_error or "Provider client is unavailable",
                error_type="ClientUnavailable",
            )

        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raise_if_task_cancelled()
            content = response.choices[0].message.content or ""
            usage = self._extract_usage(response)
            if trace is not None:
                trace.record(
                    "tool_result",
                    {
                        "summary": "模型响应返回",
                        "detail": {
                            "tool": "llm_chat",
                            "channel": channel,
                            "provider": self._provider,
                            "provider_id": self._provider_id,
                            "provider_name": self._provider_name,
                            "provider_type": self._provider_type,
                            "base_url": self._api_url,
                            "model": self._model,
                            "usage": usage.as_dict(),
                            "fallback": False,
                            "llm": {
                                "channel": channel,
                                "provider": self._provider,
                                "model": self._model,
                                **usage.as_dict(),
                                "fallback": False,
                            },
                            "content": content[:1200],
                            "raw_name": "llm_chat_response",
                        },
                    },
                )
            return {
                "content": content,
                "usage": usage.as_dict(),
                "fallback": False,
            }
        except TaskCancelled:
            raise
        except APIError as exc:
            logger.error("LLMClient API error: %s", exc)
            return self._fallback_metadata(
                trace=trace,
                channel=channel,
                error=str(exc),
                error_type=type(exc).__name__,
            )
        except Exception as exc:
            logger.error("LLMClient unexpected error: %s", exc)
            return self._fallback_metadata(
                trace=trace,
                channel=channel,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def _fallback_metadata(
        self,
        *,
        trace: Any | None,
        channel: str,
        error: str,
        error_type: str,
    ) -> dict[str, object]:
        usage = LLMUsage(usage_source="unavailable").as_dict()
        if trace is not None:
            trace.record(
                "tool_result",
                {
                    "summary": "模型调用降级",
                    "level": "audit",
                    "detail": {
                        "tool": "llm_chat",
                        "channel": channel,
                        "provider": self._provider,
                        "provider_id": self._provider_id,
                        "provider_name": self._provider_name,
                        "provider_type": self._provider_type,
                        "base_url": self._api_url,
                        "model": self._model,
                        "usage": usage,
                        "fallback": True,
                        "llm": {
                            "channel": channel,
                            "provider": self._provider,
                            "model": self._model,
                            **usage,
                            "fallback": True,
                        },
                        "severity": "warning",
                        "error": error,
                        "error_type": error_type,
                        "raw_name": "llm_chat_fallback",
                    },
                },
            )
        return {
            "content": _FALLBACK_MESSAGE,
            "usage": usage,
            "fallback": True,
            "error": error,
            "error_type": error_type,
        }

    def discover_models(self) -> dict[str, object]:
        """Probe the OpenAI-compatible models endpoint without assuming support."""
        if not self._enabled:
            return {
                "status": "unavailable",
                "models": [],
                "error": "API key is not configured",
            }
        client = self._ensure_client()
        if client is None:
            return {
                "status": "failed",
                "models": [],
                "error": self._client_init_error or "Provider client is unavailable",
            }
        try:
            response = client.models.list()
            models = sorted(
                {
                    str(getattr(item, "id", "") or "").strip()
                    for item in getattr(response, "data", [])
                    if str(getattr(item, "id", "") or "").strip()
                }
            )
            return {"status": "available", "models": models, "error": ""}
        except Exception as exc:
            logger.warning(
                "LLMClient model discovery failed for provider_id=%s: %s",
                self._provider_id,
                exc,
            )
            return {
                "status": "unsupported_or_failed",
                "models": [],
                "error": str(exc),
            }

    @staticmethod
    def _extract_usage(response: object) -> LLMUsage:
        usage_obj = getattr(response, "usage", None)
        if usage_obj is None:
            return LLMUsage(usage_source="unavailable")

        prompt_tokens = getattr(usage_obj, "prompt_tokens", None)
        completion_tokens = getattr(usage_obj, "completion_tokens", None)
        total_tokens = getattr(usage_obj, "total_tokens", None)

        if prompt_tokens is None and completion_tokens is None and total_tokens is None:
            return LLMUsage(usage_source="unavailable")

        return LLMUsage(
            prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
            completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
            total_tokens=int(total_tokens) if total_tokens is not None else None,
            usage_source="provider",
        )

    def _ensure_client(self):
        if not self._enabled:
            return None
        if self._client is not None:
            return self._client
        try:
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._api_url,
                timeout=self._timeout,
            )
            self._client_init_error = None
            return self._client
        except Exception as exc:
            error_msg = str(exc)
            if "socks" in error_msg.lower() and "socksio" in error_msg.lower():
                import httpx as _httpx
                logger.warning(
                    "SOCKS proxy detected but socksio missing, retrying with no proxy for provider_id=%s",
                    self._provider_id,
                )
                try:
                    self._client = OpenAI(
                        api_key=self._api_key,
                        base_url=self._api_url,
                        timeout=self._timeout,
                        http_client=_httpx.Client(proxy=None),
                    )
                    self._client_init_error = None
                    return self._client
                except Exception as retry_exc:
                    self._client_init_error = str(retry_exc)
                    logger.error(
                        "LLMClient initialization error (retry) for provider_id=%s: %s",
                        self._provider_id,
                        retry_exc,
                    )
                    return None
            self._client_init_error = error_msg
            logger.error(
                "LLMClient initialization error for provider_id=%s base_url=%s: %s",
                self._provider_id,
                self._api_url,
                exc,
            )
            return None
