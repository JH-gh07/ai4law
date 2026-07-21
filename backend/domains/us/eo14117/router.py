"""US 14117 API routes — EO 14117 compliance assessment endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.services.task_access import claim_task_access, require_task_access
from backend.services.runtime_health import require_healthy_llm
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.domains.us.eo14117.schema import (
    US14117AsyncAccepted,
    US14117AsyncStatus,
    US14117Request,
    US14117Result,
)
from backend.domains.us.eo14117.service import US14117Service

router = APIRouter(prefix="/us_14117", tags=["us_14117"])
service = US14117Service()


@router.post("/generate", response_model=US14117Result, dependencies=[Depends(require_healthy_llm)])
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


@router.post("/generate_async", response_model=US14117AsyncAccepted, dependencies=[Depends(require_healthy_llm)])
def generate_us_14117_async(
    payload: US14117Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> US14117AsyncAccepted:
    accepted = service.submit_async(payload)
    claim_task_access(db, task_id=accepted.task_id, user_id=current_user.id, module="us_14117")
    return accepted


@router.get("/tasks/{task_id}", response_model=US14117AsyncStatus)
def get_us_14117_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> US14117AsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
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


@router.post("/tasks/{task_id}/retry", response_model=US14117AsyncStatus)
def retry_us_14117_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> US14117AsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
