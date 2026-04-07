from fastapi import APIRouter, HTTPException

from backend.modules.pipia.schema import (
    PIPIAAsyncAccepted,
    PIPIAAsyncStatus,
    PIPIARequest,
    PIPIAResult,
)
from backend.modules.pipia.service import PIPIAService

router = APIRouter(tags=["pipia"])
service = PIPIAService()


@router.post("/pipia/generate", response_model=PIPIAResult)
def generate_pipia(payload: PIPIARequest) -> PIPIAResult:
    return service.generate_report(payload)


@router.post("/pipia/generate_async", response_model=PIPIAAsyncAccepted)
def generate_pipia_async(payload: PIPIARequest) -> PIPIAAsyncAccepted:
    return service.submit_async(payload)


@router.get("/pipia/tasks/{task_id}", response_model=PIPIAAsyncStatus)
def get_pipia_task(task_id: str) -> PIPIAAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/pipia/tasks/{task_id}/retry", response_model=PIPIAAsyncStatus)
def retry_pipia_task(task_id: str) -> PIPIAAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

