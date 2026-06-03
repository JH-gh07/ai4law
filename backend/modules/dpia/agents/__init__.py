"""DPIA Agent layer — 9 specialized GDPR DPIA agents.

Architecture per doc/tmp/dpia Section 12 (3-phase rollout):
  Phase 1 (core): Necessity & Proportionality, Risk Assessment, Mitigation Mapping, DPO/Prior Consultation
  Phase 2 (generation): External DPIA Draft, Internal Review, Consistency/Repair
  Phase 3 (front-end): DPIA Need, Processing Activity

Each agent has a narrow, constrained domain and returns structured JSON.
Agent failures never block the pipeline — they silently fall back to deterministic results.

Reference: doc/tmp/dpia — DPIA Agent 总体接入位置 & 各 Agent 具体处理逻辑
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_DPIA_SYSTEM_PROMPT = (
    "You are an EU data protection law specialist. Your expertise covers GDPR Article 35 "
    "(DPIA), WP29 WP248 rev.01 (high-risk criteria), EDPB DPIA guidelines, ICO DPIA template, "
    "Article 29 Working Party opinions, and CJEU case law. "
    "Output ONLY valid JSON. Never include explanatory text outside the JSON structure. "
    "When facts are uncertain, mark confidence accordingly. "
    "Never invent facts, regulations, or citations. "
    "Never write that a risk is 'fully eliminated'. "
    "Always distinguish 'planned' measures from 'implemented' measures."
)


class DPIAAgentBase:
    """Base class for all DPIA agents. Follows the same pattern as BCR/SCC agents."""

    agent_name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 1200

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    @property
    def enabled(self) -> bool:
        return self.llm_client is not None and self.llm_client.enabled

    def _call_llm(self, user_prompt: str, system_prompt: str | None = None) -> dict | None:
        if not self.enabled:
            return None
        try:
            raw = self.llm_client.chat(
                system=system_prompt or _DPIA_SYSTEM_PROMPT,
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
            logger.warning("DPIA Agent %s failed: %s", self.agent_name, exc)
            return None

    def run(self, **kwargs) -> dict | list[dict]:
        raise NotImplementedError


# ── Agent factory ──

def create_dpia_agents(llm_client: LLMClient | None = None) -> dict[str, DPIAAgentBase]:
    """Create all DPIA agents. Import deferred to avoid circular imports."""
    from backend.modules.dpia.agents.dpia_need_agent import DPIANeedAgent
    from backend.modules.dpia.agents.processing_activity_agent import ProcessingActivityAgent
    from backend.modules.dpia.agents.necessity_proportionality_agent import NecessityProportionalityAgent
    from backend.modules.dpia.agents.risk_assessment_agent import RiskAssessmentAgent
    from backend.modules.dpia.agents.mitigation_mapping_agent import MitigationMappingAgent
    from backend.modules.dpia.agents.dpo_consultation_agent import DPOConsultationAgent
    from backend.modules.dpia.agents.external_draft_agent import ExternalDPIAgent
    from backend.modules.dpia.agents.internal_review_agent import InternalReviewAgent
    from backend.modules.dpia.agents.consistency_repair_agent import ConsistencyRepairAgent

    return {
        "dpia_need": DPIANeedAgent(llm_client),
        "processing_activity": ProcessingActivityAgent(llm_client),
        "necessity_proportionality": NecessityProportionalityAgent(llm_client),
        "risk_assessment": RiskAssessmentAgent(llm_client),
        "mitigation_mapping": MitigationMappingAgent(llm_client),
        "dpo_consultation": DPOConsultationAgent(llm_client),
        "external_draft": ExternalDPIAgent(llm_client),
        "internal_review": InternalReviewAgent(llm_client),
        "consistency_repair": ConsistencyRepairAgent(llm_client),
    }
