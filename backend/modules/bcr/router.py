from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.modules.bcr.schema import BCRAsyncAccepted, BCRAsyncStatus, BCRRequest, BCRResult
from backend.modules.bcr.service import BCRService

router = APIRouter(tags=["bcr"])
service = BCRService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/bcr/generate", response_model=BCRResult)
def generate_bcr(
    payload: BCRRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> BCRResult:
    result = trace_sync("bcr", lambda: service.generate_report(payload))
    register_module_result_artifacts(
        db=db,
        container=container,
        user=current_user,
        module_key="bcr",
        result=result,
    )
    return result


@router.post("/bcr/generate_async", response_model=BCRAsyncAccepted)
def generate_bcr_async(
    payload: BCRRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> BCRAsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/bcr/tasks/{task_id}", response_model=BCRAsyncStatus)
def get_bcr_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> BCRAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="bcr",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/bcr/tasks/{task_id}/retry", response_model=BCRAsyncStatus)
def retry_bcr_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> BCRAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
