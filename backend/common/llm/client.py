from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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
        self._provider = settings.resolved_llm_provider
        self._model = settings.resolved_llm_model
        self._api_key = settings.resolved_llm_api_key
        self._api_url = settings.resolved_llm_api_url
        self._enabled = bool(self._api_key) and OpenAI is not None
        if self._enabled:
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._api_url,
                timeout=60,
            )
        elif OpenAI is None:
            logger.warning("LLMClient: openai package not installed, falling back to placeholder outputs.")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """发送一轮对话，返回模型回复文本。

        如果 API 未配置或调用失败，返回降级占位文本（不抛异常）。
        """
        trace = current_trace.get()
        if trace is not None:
            trace.record(
                "llm_chat_request",
                {
                    "provider": self._provider,
                    "model": self._model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "system": system,
                    "user": user,
                },
            )

        if not self._enabled:
            logger.warning("LLMClient: API key not configured for provider %s, returning fallback text.", self._provider)
            return _FALLBACK_MESSAGE

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            if trace is not None:
                trace.record("llm_chat_response", {"content": content})
            return content
        except APIError as exc:
            logger.error("LLMClient API error: %s", exc)
            return _FALLBACK_MESSAGE
        except Exception as exc:
            logger.error("LLMClient unexpected error: %s", exc)
            return _FALLBACK_MESSAGE
