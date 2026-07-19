"""Refresh runtime-configurable clients across active module instances."""

from __future__ import annotations

from backend.common.llm.client import LLMClient
from backend.integrations.delilegal import DeliLegalService


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
    from backend.domains.cn.scc_review.router import service as scc_service
    from backend.domains.cn.security_assessment.router import (
        service as assessment_service,
    )
    from backend.domains.cn.transfer_diagnosis.router import (
        renderer as diagnosis_renderer,
    )
    from backend.domains.eu.bcr_review.router import service as bcr_service
    from backend.domains.eu.dpia.router import service as dpia_service
    from backend.domains.eu.tia.router import service as tia_service
    from backend.domains.us.cpra.router import service as cpra_service
    from backend.domains.us.eo14117_flow_review.router import (
        service as eo14117_flow_service,
    )

    rag_retriever._service.cache_clear()
    rag_retriever._default_legal_service = container.legal_api_service
    rag_retriever._default_legal_service_loaded = True

    assessment_service.generator.llm = container.llm_client
    assessment_service.retriever.legal_service = container.legal_api_service

    scc_service.llm_client = container.llm_client
    pipia_service.llm_client = container.llm_client
    bcr_service.llm_client = container.llm_client
    dpia_service.llm_client = container.llm_client
    tia_service.llm_client = container.llm_client
    eo14117_flow_service.llm_client = container.llm_client
    cpra_service.llm_client = container.llm_client
    diagnosis_renderer.llm_client = container.llm_client

    v0_gateway_service.assessment.generator.llm = container.llm_client
    v0_gateway_service.assessment.retriever.legal_service = (
        container.legal_api_service
    )
    v0_gateway_service.pipia.llm_client = container.llm_client
    v0_gateway_service.bcr.llm_client = container.llm_client
    v0_gateway_service.dpia.llm_client = container.llm_client
    v0_gateway_service.tia.llm_client = container.llm_client
    v0_gateway_service.cn_flow.llm_client = container.llm_client
    v0_gateway_service.cpra.llm_client = container.llm_client
