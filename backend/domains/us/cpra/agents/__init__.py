"""CPRA agent layer — structured fact enhancement above deterministic rules.

Agents enhance non-structured facts before the rule engine runs.
Any agent failure must silently degrade to deterministic fallback behavior.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

from backend.core.json_utils import repair_llm_json

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
        if os.getenv("AI4LAW_CPRA_DISABLE_AGENT_LLM") == "1":
            return False
        return self.llm_client is not None and self.llm_client.enabled

    def _call_llm(self, user_prompt: str) -> dict | None:
        if not self.enabled:
            return None
        raw = ""
        start = -1
        end = 0
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
            # Attempt JSON repair before giving up
            json_str = raw[start:end] if start != -1 and end > 0 else ""
            if json_str:
                try:
                    repaired = repair_llm_json(json_str)
                    if repaired != json_str:
                        return json.loads(repaired)
                except Exception:
                    pass
            logger.warning("Agent %s failed: %s", self.agent_name, exc)
            return None


from backend.domains.us.cpra.agents.fact_extraction_agent import CPRAFactExtractionAgent
from backend.domains.us.cpra.agents.spi_sharing_risk_agent import CPRASPISharingRiskAgent
from backend.domains.us.cpra.agents.vendor_contract_agent import CPRAVendorContractAgent
from backend.domains.us.cpra.agents.consistency_review_agent import CPRAConsistencyReviewAgent


def create_cpra_agents(llm_client: "LLMClient | None" = None) -> dict[str, CPRAAgentBase]:
    return {
        "fact_extraction": CPRAFactExtractionAgent(llm_client),
        "spi_sharing_risk": CPRASPISharingRiskAgent(llm_client),
        "vendor_contract": CPRAVendorContractAgent(llm_client),
        "consistency_review": CPRAConsistencyReviewAgent(llm_client),
    }
