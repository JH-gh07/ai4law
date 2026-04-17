from fastapi import APIRouter

from backend.api import artifacts, copilot, diagnosis, knowledge, review, system_settings

api_router = APIRouter()
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(copilot.router, prefix="/copilot", tags=["copilot"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(system_settings.router, prefix="/system", tags=["system"])
