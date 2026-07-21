"""Refresh runtime-configurable clients across active module instances."""

from __future__ import annotations

from backend.common.llm.client import LLMClient
from backend.integrations.delilegal import DeliLegalService


def _rebind_llm_consumers(service, llm_client) -> None:
    """Rebind the known client holders inside one long-lived module service."""
    if hasattr(service, "llm_client"):
        service.llm_client = llm_client

    for child_name in (
        "generator",
        "renderer",
        "type_classifier",
        "clause_reviewer",
        "reviewer",
    ):
        child = getattr(service, child_name, None)
        if child is None:
            continue
        if hasattr(child, "llm_client"):
            child.llm_client = llm_client
        if hasattr(child, "llm"):
            child.llm = llm_client

    agents = getattr(service, "agents", None)
    if isinstance(agents, dict):
        for agent in agents.values():
            if hasattr(agent, "llm_client"):
                agent.llm_client = llm_client


def refresh_runtime_clients(container) -> None:
    """Rebind runtime clients without putting domain imports in core config code."""

    container.llm_client = LLMClient(container.settings)
    container.legal_api_service = DeliLegalService(container.settings)

    container.diagnosis_service.llm_client = container.llm_client
    container.diagnosis_service.legal_api_service = container.legal_api_service

    container.review_service.knowledge_base.legal_api_service = (
        container.legal_api_service
    )
    container.review_service.reviewer.llm_client = container.llm_client

    from backend.common.rag import retriever as rag_retriever
    from backend.api.v0.task_gateway.router import service as v0_gateway_service
    from backend.domains.cn.pipia.router import service as pipia_service
    from backend.domains.cn.security_assessment.router import (
        service as assessment_service,
    )
    from backend.domains.cn.transfer_diagnosis.router import (
        renderer as diagnosis_renderer,
    )
    from backend.domains.eu.bcr_review.router import service as bcr_service
    from backend.domains.eu.dpia.router import service as dpia_service
    from backend.domains.eu.scc_review.router import service as scc_service
    from backend.domains.eu.tia.router import service as tia_service
    from backend.domains.us.cpra.router import service as cpra_service
    from backend.domains.us.eo14117.router import service as eo14117_service
    from backend.domains.us.eo14117_flow_review.router import (
        service as eo14117_flow_service,
    )

    rag_retriever._service.cache_clear()
    rag_retriever._default_legal_service = container.legal_api_service
    rag_retriever._default_legal_service_loaded = True

    assessment_service.retriever.legal_service = container.legal_api_service
    for service in (
        container.diagnosis_service,
        container.review_service,
        diagnosis_renderer,
        assessment_service,
        pipia_service,
        scc_service,
        bcr_service,
        dpia_service,
        tia_service,
        eo14117_flow_service,
        cpra_service,
        eo14117_service,
    ):
        _rebind_llm_consumers(service, container.llm_client)

    v0_gateway_service.assessment.generator.llm = container.llm_client
    v0_gateway_service.assessment.retriever.legal_service = (
        container.legal_api_service
    )
    for service in (
        v0_gateway_service.assessment,
        v0_gateway_service.pipia,
        v0_gateway_service.bcr,
        v0_gateway_service.dpia,
        v0_gateway_service.tia,
        v0_gateway_service.cn_flow,
        v0_gateway_service.cpra,
    ):
        _rebind_llm_consumers(service, container.llm_client)
