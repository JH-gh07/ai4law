from fastapi import APIRouter, HTTPException

from backend.modules.scc.schema import SCCAsyncAccepted, SCCAsyncStatus, SCCRequest, SCCResult
from backend.modules.scc.service import SCCService

router = APIRouter(tags=["scc"])
service = SCCService()


@router.post("/scc/generate", response_model=SCCResult)
def generate_scc(payload: SCCRequest) -> SCCResult:
    return service.generate_report(payload)


@router.post("/scc/generate_async", response_model=SCCAsyncAccepted)
def generate_scc_async(payload: SCCRequest) -> SCCAsyncAccepted:
    return service.submit_async(payload)


@router.get("/scc/tasks/{task_id}", response_model=SCCAsyncStatus)
def get_scc_task(task_id: str) -> SCCAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/scc/tasks/{task_id}/retry", response_model=SCCAsyncStatus)
def retry_scc_task(task_id: str) -> SCCAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
