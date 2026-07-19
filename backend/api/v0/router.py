from fastapi import APIRouter

from backend.api.v0.task_gateway.router import router as task_gateway_router

v0_router = APIRouter()
v0_router.include_router(task_gateway_router)
