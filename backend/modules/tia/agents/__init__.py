"""TIA Agent layer — 3 precision agents above deterministic rule engine.

Agents enhance, not replace, the rule engine:
- RAGPlanningAgent: multi-query retrieval planning
- AttachmentReviewAgent: deep evidence review beyond keyword matching
- DPOReviewAgent: compliance quality gate before report generation
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_TIA_SYSTEM_PROMPT = (
    "You are an EU data protection officer (DPO) specializing in Transfer Impact "
    "Assessments (TIA) under GDPR, Schrems II (C-311/18), EDPB Recommendations "
    "01/2020, and SCC 2021/914. You review TIA documentation for regulatory adequacy. "
    "Output ONLY valid JSON. Never include explanatory text outside the JSON structure. "
    "When evidence is insufficient, mark it and recommend specific additional documentation."
)


class TIAAgentBase:
    agent_name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 600

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
                system=_TIA_SYSTEM_PROMPT, user=user_prompt,
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

    def run(self, **kwargs) -> dict:
        raise NotImplementedError


from backend.modules.tia.agents.rag_planning_agent import RAGPlanningAgent
from backend.modules.tia.agents.attachment_review_agent import AttachmentReviewAgent
from backend.modules.tia.agents.dpo_review_agent import DPOReviewAgent


def create_tia_agents(llm_client: LLMClient | None = None) -> dict:
    return {
        "rag_planning": RAGPlanningAgent(llm_client),
        "attachment_review": AttachmentReviewAgent(llm_client),
        "dpo_review": DPOReviewAgent(llm_client),
    }
