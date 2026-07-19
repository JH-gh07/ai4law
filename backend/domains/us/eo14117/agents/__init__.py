"""US14117 Agent layer — 5 reasoning agents above deterministic rule engine.

Agents are invoked AFTER the rule engine produces its output.
Each agent handles a specific boundary / optimization / verification task.
Agent failures silently return rule-engine defaults (no pipeline blocking).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_US14117_SYSTEM_PROMPT = (
    "You are a US trade compliance lawyer specializing in EO 14117 "
    "(Preventing Access to Americans' Bulk Sensitive Personal Data and "
    "United States Government-Related Data by Countries of Concern). "
    "You analyze data transactions for prohibited (§100.2) and restricted "
    "(§100.3) classifications. Output ONLY valid JSON. "
    "When facts are uncertain, mark them and explain why."
)


class US14117AgentBase:
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
                system=_US14117_SYSTEM_PROMPT, user=user_prompt,
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


# ── Agent imports ──

from backend.domains.us.eo14117.agents.rule_boundary_agent import RuleBoundaryAgent
from backend.domains.us.eo14117.agents.evidence_priority_agent import EvidencePriorityAgent
from backend.domains.us.eo14117.agents.rag_reformulation_agent import RAGReformulationAgent
from backend.domains.us.eo14117.agents.chapter_consistency_agent import ChapterConsistencyAgent
from backend.domains.us.eo14117.agents.repair_check_agent import RepairCheckAgent


def create_us14117_agents(llm_client: LLMClient | None = None) -> dict:
    return {
        "rule_boundary": RuleBoundaryAgent(llm_client),
        "evidence_priority": EvidencePriorityAgent(llm_client),
        "rag_reformulation": RAGReformulationAgent(llm_client),
        "chapter_consistency": ChapterConsistencyAgent(llm_client),
        "repair_check": RepairCheckAgent(llm_client),
    }
