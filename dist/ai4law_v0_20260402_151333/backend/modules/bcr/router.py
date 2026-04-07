from fastapi import APIRouter, HTTPException

from backend.modules.bcr.schema import BCRAsyncAccepted, BCRAsyncStatus, BCRRequest, BCRResult
from backend.modules.bcr.service import BCRService

router = APIRouter(tags=["bcr"])
service = BCRService()


@router.post("/bcr/generate", response_model=BCRResult)
def generate_bcr(payload: BCRRequest) -> BCRResult:
    return service.generate_report(payload)


@router.post("/bcr/generate_async", response_model=BCRAsyncAccepted)
def generate_bcr_async(payload: BCRRequest) -> BCRAsyncAccepted:
    return service.submit_async(payload)


@router.get("/bcr/tasks/{task_id}", response_model=BCRAsyncStatus)
def get_bcr_task(task_id: str) -> BCRAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/bcr/tasks/{task_id}/retry", response_model=BCRAsyncStatus)
def retry_bcr_task(task_id: str) -> BCRAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

