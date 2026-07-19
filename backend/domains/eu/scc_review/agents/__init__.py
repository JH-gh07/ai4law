"""EU SCC Agent layer — 6 specialist agents augmenting the deterministic rule engine.

Architecture: Agents intervene at specific points in the pipeline to handle
tasks that rules alone cannot reliably cover. Each agent returns structured JSON.
Agent failures never block the pipeline — they silently fall back to rule results.

Agent 1: DocumentStructureAgent    — completes parsed fields, flags uncertain items
Agent 2: TransferChainAgent         — infers full data flow including hidden processors
Agent 3: ClauseSemanticAgent        — semantic-level clause comparison vs EU 2021/914
Agent 4: TIAEffectivenessAgent     — evaluates whether measures can resist third-country access
Agent 5: EvidenceReviewAgent       — reviews evidence precision per issue
Agent 6: RemediationAgent          — generates insertable clause-level fix suggestions
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_EU_SCC_SYSTEM_PROMPT = (
    "You are an EU data protection lawyer specializing in Standard Contractual Clauses "
    "(EU 2021/914) and cross-border data transfers under GDPR Articles 44-49. "
    "Output ONLY valid JSON. Never include explanatory text outside the JSON structure."
)


class SCCAgentBase:
    agent_name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 600

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    @property
    def enabled(self) -> bool:
        return self.llm_client is not None and getattr(self.llm_client, "enabled", False)

    def _call_llm(self, user_prompt: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            raw = self.llm_client.chat(
                system=_EU_SCC_SYSTEM_PROMPT, user=user_prompt,
                temperature=self.temperature, max_tokens=self.max_tokens,
            )
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            return json.loads(raw[start:end])
        except Exception as exc:
            logger.warning("EU SCC Agent %s failed: %s", self.agent_name, exc)
            return None

    def run(self, **kwargs) -> dict:
        raise NotImplementedError


# ── Agent factory ──
from backend.domains.eu.scc_review.agents.document_structure_agent import DocumentStructureAgent
from backend.domains.eu.scc_review.agents.transfer_chain_agent import TransferChainAgent
from backend.domains.eu.scc_review.agents.clause_semantic_agent import ClauseSemanticAgent
from backend.domains.eu.scc_review.agents.tia_effectiveness_agent import TIAEffectivenessAgent
from backend.domains.eu.scc_review.agents.evidence_review_agent import EvidenceReviewAgent
from backend.domains.eu.scc_review.agents.remediation_agent import RemediationAgent

def create_eu_scc_agents(llm_client: LLMClient | None = None) -> dict[str, SCCAgentBase]:
    return {
        "document_structure": DocumentStructureAgent(llm_client),
        "transfer_chain": TransferChainAgent(llm_client),
        "clause_semantic": ClauseSemanticAgent(llm_client),
        "tia_effectiveness": TIAEffectivenessAgent(llm_client),
        "evidence_review": EvidenceReviewAgent(llm_client),
        "remediation": RemediationAgent(llm_client),
    }
