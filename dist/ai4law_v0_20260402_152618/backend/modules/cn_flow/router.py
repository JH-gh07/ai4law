from fastapi import APIRouter, HTTPException

from backend.modules.cn_flow.schema import (
    CNFlowAsyncAccepted,
    CNFlowAsyncStatus,
    CNFlowRequest,
    CNFlowResult,
)
from backend.modules.cn_flow.service import CNFlowService

router = APIRouter(tags=["cn-flow"])
service = CNFlowService()


@router.post("/cn-flow/generate", response_model=CNFlowResult)
def generate_cn_flow(payload: CNFlowRequest) -> CNFlowResult:
    return service.generate_report(payload)


@router.post("/cn-flow/generate_async", response_model=CNFlowAsyncAccepted)
def generate_cn_flow_async(payload: CNFlowRequest) -> CNFlowAsyncAccepted:
    return service.submit_async(payload)


@router.get("/cn-flow/tasks/{task_id}", response_model=CNFlowAsyncStatus)
def get_cn_flow_task(task_id: str) -> CNFlowAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cn-flow/tasks/{task_id}/retry", response_model=CNFlowAsyncStatus)
def retry_cn_flow_task(task_id: str) -> CNFlowAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

