"""CPRA agent layer — structured fact enhancement above deterministic rules.

Agents enhance non-structured facts before the rule engine runs.
Any agent failure must silently degrade to deterministic fallback behavior.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_CPRA_SYSTEM_PROMPT = (
    "You are a California privacy compliance lawyer specialized in CPRA/CCPA. "
    "You extract structured compliance facts from policies, SOPs, vendor materials, "
    "and data maps. Output only valid JSON and preserve uncertainty explicitly."
)


class CPRAAgentBase:
    agent_name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 800

    def __init__(self, llm_client: "LLMClient | None" = None) -> None:
        self.llm_client = llm_client

    @property
    def enabled(self) -> bool:
        return self.llm_client is not None and self.llm_client.enabled

    def _call_llm(self, user_prompt: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            raw = self.llm_client.chat(
                system=_CPRA_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            return json.loads(raw[start:end])
        except Exception as exc:
            logger.warning("Agent %s failed: %s", self.agent_name, exc)
            return None


from backend.modules.cpra.agents.fact_extraction_agent import CPRAFactExtractionAgent


def create_cpra_agents(llm_client: "LLMClient | None" = None) -> dict[str, CPRAAgentBase]:
    return {
        "fact_extraction": CPRAFactExtractionAgent(llm_client),
    }
