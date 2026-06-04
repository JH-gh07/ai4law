from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.modules.tia.schema import TIAAsyncAccepted, TIAAsyncStatus, TIARequest, TIAResult
from backend.modules.tia.service import TIAService

router = APIRouter(tags=["tia"])
service = TIAService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tia/generate", response_model=TIAResult)
def generate_tia(
    payload: TIARequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> TIAResult:
    result = trace_sync("tia", lambda: service.generate_report(payload))
    register_module_result_artifacts(
        db=db,
        container=container,
        user=current_user,
        module_key="tia",
        result=result,
    )
    return result


@router.post("/tia/generate_async", response_model=TIAAsyncAccepted)
def generate_tia_async(
    payload: TIARequest,
    current_user: AuthUser = Depends(get_current_user),
) -> TIAAsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/tia/tasks/{task_id}", response_model=TIAAsyncStatus)
def get_tia_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> TIAAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="tia",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tia/tasks/{task_id}/retry", response_model=TIAAsyncStatus)
def retry_tia_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> TIAAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
