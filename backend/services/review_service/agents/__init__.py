"""Document Review Agent layer — 9 precision agents for complex compliance judgment.

Agents enhance, not replace, the 8-stage pipeline:
- P0: ScenarioFactsAgent, DataSensitivityAgent, SccMandatoryClauseAgent
- P1: PrivacyNoticeMatrixAgent, CrossDocSemanticAgent, LegalBindingAgent
- P2: RevisionDraftingAgent, ReviewBoundaryAgent, ReportQAAgent
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_REVIEW_SYSTEM_PROMPT = (
    "你是一名精通中国数据跨境合规的资深律师，深度掌握《个人信息保护法》"
    "《数据安全法》《网络安全法》《数据出境安全评估办法》《个人信息出境标准合同办法》"
    "及相关配套法规和标准。请基于提供的事实和法规，给出专业判断。"
    "输出 ONLY 有效 JSON，不要任何解释性文字。"
    "当事实不足以确定时，明确标注为不确定并给出需补充的信息。"
)


class ReviewAgentBase:
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
                system=_REVIEW_SYSTEM_PROMPT, user=user_prompt,
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


from backend.services.review_service.agents.scenario_facts_agent import ScenarioFactsAgent
from backend.services.review_service.agents.data_sensitivity_agent import DataSensitivityAgent
from backend.services.review_service.agents.scc_mandatory_clause_agent import SccMandatoryClauseAgent
from backend.services.review_service.agents.privacy_notice_matrix_agent import PrivacyNoticeMatrixAgent
from backend.services.review_service.agents.cross_doc_semantic_agent import CrossDocSemanticAgent
from backend.services.review_service.agents.legal_binding_agent import LegalBindingAgent
from backend.services.review_service.agents.revision_drafting_agent import RevisionDraftingAgent
from backend.services.review_service.agents.review_boundary_agent import ReviewBoundaryAgent
from backend.services.review_service.agents.report_qa_agent import ReportQAAgent


def create_review_agents(llm_client: LLMClient | None = None) -> dict:
    return {
        "scenario_facts": ScenarioFactsAgent(llm_client),
        "data_sensitivity": DataSensitivityAgent(llm_client),
        "scc_mandatory": SccMandatoryClauseAgent(llm_client),
        "privacy_notice": PrivacyNoticeMatrixAgent(llm_client),
        "cross_doc_semantic": CrossDocSemanticAgent(llm_client),
        "legal_binding": LegalBindingAgent(llm_client),
        "revision_drafting": RevisionDraftingAgent(llm_client),
        "review_boundary": ReviewBoundaryAgent(llm_client),
        "report_qa": ReportQAAgent(llm_client),
    }
