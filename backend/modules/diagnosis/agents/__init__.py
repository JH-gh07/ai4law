"""Diagnosis Agent layer — 4 precision agents for ambiguous fact clarification.

Agents are invoked DURING the diagnosis flow to help resolve "unknown" / fuzzy
answers. They DO NOT make the final path decision — the decision tree does.
Agent failures silently return None (no pipeline blocking).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_DIAG_SYSTEM_PROMPT = (
    "你是一名精通中国数据跨境合规的资深律师，深度掌握《个人信息保护法》"
    "《数据安全法》《数据出境安全评估办法》《促进和规范数据跨境流动规定》"
    "及相关部门规章。请根据用户提供的业务信息，辅助判断关键合规事实。"
    "输出 ONLY 有效 JSON，不要任何解释性文字。"
    "当事实不足以确定时，明确标注为低置信度并给出需补充的信息。"
)


class DiagAgentBase:
    agent_name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 500

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    @property
    def enabled(self) -> bool:
        return self.llm_client is not None and self.llm_client.enabled

    def _call_llm(self, user_prompt: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            raw = self.llm_client.chat(
                system=_DIAG_SYSTEM_PROMPT, user=user_prompt,
                temperature=self.temperature, max_tokens=self.max_tokens,
            )
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            return json.loads(raw[start:end])
        except Exception as exc:
            logger.warning("Agent %s failed: %s", self.agent_name, exc)
            return None

    def run(self, **kwargs) -> dict | None:
        raise NotImplementedError


from backend.modules.diagnosis.agents.important_data_agent import ImportantDataAgent
from backend.modules.diagnosis.agents.clarification_agent import ClarificationAgent
from backend.modules.diagnosis.agents.pi_classify_agent import PIClassifyAgent
from backend.modules.diagnosis.agents.exemption_agent import ExemptionAgent


def create_diag_agents(llm_client: LLMClient | None = None) -> dict:
    return {
        "important_data": ImportantDataAgent(llm_client),
        "clarification": ClarificationAgent(llm_client),
        "pi_classify": PIClassifyAgent(llm_client),
        "exemption": ExemptionAgent(llm_client),
    }
