from fastapi import APIRouter

from backend.api import artifacts, auth, citations, copilot, diagnosis, knowledge, knowledge_review, me, reports, review, system_settings, workspace_state

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(citations.router, prefix="/citations", tags=["citations"])
api_router.include_router(copilot.router, prefix="/copilot", tags=["copilot"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(workspace_state.router, prefix="/workspace-state", tags=["workspace-state"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(knowledge_review.router, prefix="/knowledge/review", tags=["knowledge-review"])
api_router.include_router(system_settings.router, prefix="/system", tags=["system"])
