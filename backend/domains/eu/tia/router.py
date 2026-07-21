from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.services.task_access import claim_task_access, require_task_access
from backend.services.runtime_health import require_healthy_llm
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.domains.eu.tia.schema import TIAAsyncAccepted, TIAAsyncStatus, TIARequest, TIAResult
from backend.domains.eu.tia.service import TIAService

router = APIRouter(prefix="/tia", tags=["tia"])
service = TIAService()


@router.post("/generate", response_model=TIAResult, dependencies=[Depends(require_healthy_llm)])
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


@router.post("/generate_async", response_model=TIAAsyncAccepted, dependencies=[Depends(require_healthy_llm)])
def generate_tia_async(
    payload: TIARequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> TIAAsyncAccepted:
    accepted = service.submit_async(payload)
    claim_task_access(db, task_id=accepted.task_id, user_id=current_user.id, module="tia")
    return accepted


@router.get("/tasks/{task_id}", response_model=TIAAsyncStatus)
def get_tia_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> TIAAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
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


@router.post(
    "/tasks/{task_id}/retry",
    response_model=TIAAsyncStatus,
    dependencies=[Depends(require_healthy_llm)],
)
def retry_tia_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> TIAAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
