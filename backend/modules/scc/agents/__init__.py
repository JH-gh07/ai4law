"""CN SCC Agent layer — 9 specialized agents for compliance review.

Architecture: agents are invoked in priority order (P0 → P1 → P2).
Each agent has a narrow, constrained domain and returns structured JSON.
Agent failures never block the pipeline — they silently fall back to rule-based results.

Reference: doc/tmp/认证标准合同路径
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_CN_SCC_SYSTEM_PROMPT = (
    "You are a Chinese data protection lawyer specializing in cross-border data transfer compliance "
    "under the Personal Information Protection Law (PIPL), Data Security Law (DSL), "
    "Personal Information Security Specification (GB/T 35273), "
    "Measures on Standard Contracts for Cross-Border Transfer of Personal Information, "
    "Measures on Certification for Cross-Border Transfer of Personal Information, "
    "and related regulations. "
    "Output ONLY valid JSON. Never include explanatory text outside the JSON structure. "
    "When facts are uncertain, mark confidence accordingly and explain limitations."
)


class SCCAgentBase:
    """Base class for all CN SCC agents. Follows the same pattern as BCR agents."""

    agent_name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 800

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
                system=system_prompt or _CN_SCC_SYSTEM_PROMPT,
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

    def run(self, **kwargs) -> dict:
        raise NotImplementedError


# ── Agent factory ──

def create_scc_agents(llm_client: LLMClient | None = None) -> dict[str, SCCAgentBase]:
    """Create all CN SCC agents. Import deferred to avoid circular imports."""
    from backend.modules.scc.agents.path_diagnosis_agent import PathDiagnosisAgent
    from backend.modules.scc.agents.data_classification_agent import DataClassificationAgent
    from backend.modules.scc.agents.contract_review_agent import ContractReviewAgent
    from backend.modules.scc.agents.evidence_verification_agent import EvidenceVerificationAgent
    from backend.modules.scc.agents.legal_basis_review_agent import LegalBasisReviewAgent
    from backend.modules.scc.agents.report_review_agent import ReportReviewAgent
    from backend.modules.scc.agents.rag_planning_agent import RAGPlanningAgent
    from backend.modules.scc.agents.clarification_agent import ClarificationAgent
    from backend.modules.scc.agents.explanation_agent import ExplanationAgent

    return {
        "path_diagnosis": PathDiagnosisAgent(llm_client),
        "data_classification": DataClassificationAgent(llm_client),
        "contract_review": ContractReviewAgent(llm_client),
        "evidence_verification": EvidenceVerificationAgent(llm_client),
        "legal_basis_review": LegalBasisReviewAgent(llm_client),
        "report_review": ReportReviewAgent(llm_client),
        "rag_planning": RAGPlanningAgent(llm_client),
        "clarification": ClarificationAgent(llm_client),
        "explanation": ExplanationAgent(llm_client),
    }
