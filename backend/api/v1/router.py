from fastapi import APIRouter

from backend.api.v1.endpoints import (
    artifacts,
    auth,
    citations,
    copilot,
    diagnosis,
    events,
    knowledge,
    knowledge_review,
    me,
    reports,
    system_settings,
    workspace_state,
)
from backend.domains.cn.document_review.router import router as review_router
from backend.domains.cn.security_assessment.router import router as assessment_router
from backend.domains.eu.bcr_review.router import router as bcr_router
from backend.domains.us.eo14117_flow_review.router import router as cn_flow_router
from backend.domains.us.cpra.router import router as cpra_router
from backend.domains.cn.transfer_diagnosis.router import router as diagnosis_module_router
from backend.domains.eu.dpia.router import router as dpia_router
from backend.domains.eu.scc_review.router import router as eu_scc_router
from backend.domains.cn.pipia.router import router as pipia_router
from backend.domains.cn.scc_review.router import router as scc_router
from backend.domains.eu.tia.router import router as tia_router
from backend.domains.us.eo14117.router import router as us_14117_router

v1_router = APIRouter()

# Public and compatibility APIs.
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(me.router, prefix="/me", tags=["me"])
v1_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
v1_router.include_router(citations.router, prefix="/citations", tags=["citations"])
v1_router.include_router(copilot.router, prefix="/copilot", tags=["copilot"])
v1_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
v1_router.include_router(reports.router, prefix="/reports", tags=["reports"])
v1_router.include_router(review_router, prefix="/review", tags=["review"])
v1_router.include_router(
    workspace_state.router,
    prefix="/workspace-state",
    tags=["workspace-state"],
)
v1_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
v1_router.include_router(
    knowledge_review.router,
    prefix="/knowledge/review",
    tags=["knowledge-review"],
)
v1_router.include_router(events.router, prefix="/events", tags=["events"])
v1_router.include_router(system_settings.router, prefix="/system", tags=["system"])

# Stateless and task-based business module APIs.
v1_router.include_router(diagnosis_module_router)
v1_router.include_router(assessment_router)
v1_router.include_router(scc_router)
v1_router.include_router(pipia_router)
v1_router.include_router(bcr_router)
v1_router.include_router(dpia_router)
v1_router.include_router(eu_scc_router)
v1_router.include_router(tia_router)
v1_router.include_router(cn_flow_router)
v1_router.include_router(cpra_router)
v1_router.include_router(us_14117_router)
