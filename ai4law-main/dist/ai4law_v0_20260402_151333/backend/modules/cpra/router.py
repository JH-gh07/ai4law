from fastapi import APIRouter, HTTPException

from backend.modules.cpra.schema import CPRAAsyncAccepted, CPRAAsyncStatus, CPRARequest, CPRAResult
from backend.modules.cpra.service import CPRAService

router = APIRouter(tags=["cpra"])
service = CPRAService()


@router.post("/cpra/generate", response_model=CPRAResult)
def generate_cpra(payload: CPRARequest) -> CPRAResult:
    return service.generate_report(payload)


@router.post("/cpra/generate_async", response_model=CPRAAsyncAccepted)
def generate_cpra_async(payload: CPRARequest) -> CPRAAsyncAccepted:
    return service.submit_async(payload)


@router.get("/cpra/tasks/{task_id}", response_model=CPRAAsyncStatus)
def get_cpra_task(task_id: str) -> CPRAAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cpra/tasks/{task_id}/retry", response_model=CPRAAsyncStatus)
def retry_cpra_task(task_id: str) -> CPRAAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

