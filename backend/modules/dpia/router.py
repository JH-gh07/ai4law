from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.modules.dpia.schema import DPIAAsyncAccepted, DPIAAsyncStatus, DPIARequest, DPIAResult
from backend.modules.dpia.service import DPIAService

router = APIRouter(prefix="/dpia", tags=["dpia"])
service = DPIAService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/generate", response_model=DPIAResult)
def generate_dpia(
    payload: DPIARequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> DPIAResult:
    result = trace_sync("dpia", lambda: service.generate_report(payload))
    register_module_result_artifacts(
        db=db,
        container=container,
        user=current_user,
        module_key="dpia",
        result=result,
    )
    return result


@router.post("/generate_async", response_model=DPIAAsyncAccepted)
def generate_dpia_async(
    payload: DPIARequest,
    current_user: AuthUser = Depends(get_current_user),
) -> DPIAAsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/tasks/{task_id}", response_model=DPIAAsyncStatus)
def get_dpia_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> DPIAAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="dpia",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry", response_model=DPIAAsyncStatus)
def retry_dpia_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> DPIAAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
