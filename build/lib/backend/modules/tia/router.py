from fastapi import APIRouter, HTTPException

from backend.modules.tia.schema import TIAAsyncAccepted, TIAAsyncStatus, TIARequest, TIAResult
from backend.modules.tia.service import TIAService

router = APIRouter(tags=["tia"])
service = TIAService()


@router.post("/tia/generate", response_model=TIAResult)
def generate_tia(payload: TIARequest) -> TIAResult:
    return service.generate_report(payload)


@router.post("/tia/generate_async", response_model=TIAAsyncAccepted)
def generate_tia_async(payload: TIARequest) -> TIAAsyncAccepted:
    return service.submit_async(payload)


@router.get("/tia/tasks/{task_id}", response_model=TIAAsyncStatus)
def get_tia_task(task_id: str) -> TIAAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tia/tasks/{task_id}/retry", response_model=TIAAsyncStatus)
def retry_tia_task(task_id: str) -> TIAAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

