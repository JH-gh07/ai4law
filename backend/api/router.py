from fastapi import APIRouter

from backend.api import diagnosis, knowledge, review

api_router = APIRouter()
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
