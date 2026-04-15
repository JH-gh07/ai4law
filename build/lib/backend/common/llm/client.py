from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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
    """腾讯混元 LLM 客户端（OpenAI 兼容协议）。

    用法::

        client = LLMClient(settings)
        text = client.chat(
            system="你是一名中国数据合规律师",
            user="请分析以下条款的合规风险...",
        )
    """

    def __init__(self, settings: Settings) -> None:
        self._model = settings.llm_model
        self._enabled = bool(settings.tencent_api_key) and OpenAI is not None
        if self._enabled:
            self._client = OpenAI(
                api_key=settings.tencent_api_key,
                base_url=settings.tencent_api_url,
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
        if not self._enabled:
            logger.warning("LLMClient: API key not configured, returning fallback text.")
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
            return response.choices[0].message.content or ""
        except APIError as exc:
            logger.error("LLMClient API error: %s", exc)
            return _FALLBACK_MESSAGE
        except Exception as exc:
            logger.error("LLMClient unexpected error: %s", exc)
            return _FALLBACK_MESSAGE
