from fastapi import APIRouter, HTTPException

from backend.modules.dpia.schema import DPIAAsyncAccepted, DPIAAsyncStatus, DPIARequest, DPIAResult
from backend.modules.dpia.service import DPIAService

router = APIRouter(tags=["dpia"])
service = DPIAService()


@router.post("/dpia/generate", response_model=DPIAResult)
def generate_dpia(payload: DPIARequest) -> DPIAResult:
    return service.generate_report(payload)


@router.post("/dpia/generate_async", response_model=DPIAAsyncAccepted)
def generate_dpia_async(payload: DPIARequest) -> DPIAAsyncAccepted:
    return service.submit_async(payload)


@router.get("/dpia/tasks/{task_id}", response_model=DPIAAsyncStatus)
def get_dpia_task(task_id: str) -> DPIAAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/dpia/tasks/{task_id}/retry", response_model=DPIAAsyncStatus)
def retry_dpia_task(task_id: str) -> DPIAAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

