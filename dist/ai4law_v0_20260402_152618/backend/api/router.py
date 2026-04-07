from fastapi import APIRouter

from backend.api import diagnosis, review

api_router = APIRouter()
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
