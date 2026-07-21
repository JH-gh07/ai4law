from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.services.task_access import claim_task_access, require_task_access
from backend.services.runtime_health import require_healthy_llm
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.domains.eu.bcr_review.schema import BCRAsyncAccepted, BCRAsyncStatus, BCRRequest, BCRResult
from backend.domains.eu.bcr_review.service import BCRService

router = APIRouter(prefix="/bcr", tags=["bcr"])
service = BCRService()


@router.post("/generate", response_model=BCRResult, dependencies=[Depends(require_healthy_llm)])
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


@router.post("/generate_async", response_model=BCRAsyncAccepted, dependencies=[Depends(require_healthy_llm)])
def generate_bcr_async(
    payload: BCRRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> BCRAsyncAccepted:
    accepted = service.submit_async(payload)
    claim_task_access(db, task_id=accepted.task_id, user_id=current_user.id, module="bcr")
    return accepted


@router.get("/tasks/{task_id}", response_model=BCRAsyncStatus)
def get_bcr_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> BCRAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
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


@router.post("/tasks/{task_id}/retry", response_model=BCRAsyncStatus)
def retry_bcr_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> BCRAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
