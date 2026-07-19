"""BCR Agent layer — 10 reasoning agents above deterministic rules.

Architecture: agents are invoked AFTER rule layer produces initial findings.
Each agent has a narrow, constrained domain and returns structured JSON.
Agent failures never block the pipeline — they silently fall back to rule results.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_BCR_SYSTEM_PROMPT = (
    "You are an EU data protection lawyer specializing in Binding Corporate Rules (BCR) "
    "review under GDPR Article 47 and EDPB Recommendations 1/2022 (BCR-C) and 2/2022 (BCR-P). "
    "Output ONLY valid JSON. Never include explanatory text outside the JSON structure. "
    "When facts are uncertain, mark facts_uncertain as true and explain why."
)


class BCRAgentBase:
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
                system=_BCR_SYSTEM_PROMPT, user=user_prompt,
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


# ── Agent factory ──

from backend.domains.eu.bcr_review.agents.type_reasoning_agent import BCRTypeReasoningAgent
from backend.domains.eu.bcr_review.agents.coverage_agent import BCRRequirementCoverageAgent
from backend.domains.eu.bcr_review.agents.actor_role_agent import BCRActorRoleAgent
from backend.domains.eu.bcr_review.agents.onward_transfer_agent import BCROnwardTransferAgent
from backend.domains.eu.bcr_review.agents.tia_reasoning_agent import BCRTiaReasoningAgent
from backend.domains.eu.bcr_review.agents.evidence_coverage_agent import BCREvidenceCoverageAgent
from backend.domains.eu.bcr_review.agents.incorrect_status_agent import BCRIncorrectStatusAgent
from backend.domains.eu.bcr_review.agents.legal_grounding_agent import BCRLegalGroundingAgent
from backend.domains.eu.bcr_review.agents.approval_risk_agent import BCRApprovalRiskAgent
from backend.domains.eu.bcr_review.agents.remediation_agent import BCRRemediationAgent


def create_agents(llm_client: LLMClient | None = None) -> dict[str, BCRAgentBase]:
    return {
        "type_reasoning": BCRTypeReasoningAgent(llm_client),
        "coverage": BCRRequirementCoverageAgent(llm_client),
        "actor_role": BCRActorRoleAgent(llm_client),
        "onward_transfer": BCROnwardTransferAgent(llm_client),
        "tia_reasoning": BCRTiaReasoningAgent(llm_client),
        "evidence_coverage": BCREvidenceCoverageAgent(llm_client),
        "incorrect_status": BCRIncorrectStatusAgent(llm_client),
        "legal_grounding": BCRLegalGroundingAgent(llm_client),
        "approval_risk": BCRApprovalRiskAgent(llm_client),
        "remediation": BCRRemediationAgent(llm_client),
    }
