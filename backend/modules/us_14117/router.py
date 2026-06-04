"""US 14117 API routes — EO 14117 compliance assessment endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.modules.us_14117.schema import (
    US14117AsyncAccepted,
    US14117AsyncStatus,
    US14117Request,
    US14117Result,
)
from backend.modules.us_14117.service import US14117Service

router = APIRouter(tags=["us_14117"])
service = US14117Service()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/us_14117/generate", response_model=US14117Result)
def generate_us_14117_report(
    payload: US14117Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> US14117Result:
    result = trace_sync("us_14117", lambda: service.generate_report(payload))
    register_module_result_artifacts(
        db=db,
        container=container,
        user=current_user,
        module_key="us_14117",
        result=result,
    )
    return result


@router.post("/us_14117/generate_async", response_model=US14117AsyncAccepted)
def generate_us_14117_async(
    payload: US14117Request,
    current_user: AuthUser = Depends(get_current_user),
) -> US14117AsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/us_14117/tasks/{task_id}", response_model=US14117AsyncStatus)
def get_us_14117_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> US14117AsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="us_14117",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/us_14117/tasks/{task_id}/retry", response_model=US14117AsyncStatus)
def retry_us_14117_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> US14117AsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
