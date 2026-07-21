from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.services.task_access import claim_task_access, require_task_access
from backend.services.runtime_health import require_healthy_llm
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.common.trace.tracer import trace_sync
from backend.domains.us.cpra.schema import CPRAAsyncAccepted, CPRAAsyncStatus, CPRARequest, CPRAResult
from backend.domains.us.cpra.service import CPRAService

router = APIRouter(prefix="/cpra", tags=["cpra"])
service = CPRAService()


@router.post("/generate", response_model=CPRAResult, dependencies=[Depends(require_healthy_llm)])
def generate_cpra(
    payload: CPRARequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> CPRAResult:
    result = trace_sync("cpra", lambda: service.generate_report(payload))
    register_module_result_artifacts(
        db=db,
        container=container,
        user=current_user,
        module_key="cpra",
        result=result,
    )
    return result


@router.post("/generate_async", response_model=CPRAAsyncAccepted, dependencies=[Depends(require_healthy_llm)])
def generate_cpra_async(
    payload: CPRARequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> CPRAAsyncAccepted:
    accepted = service.submit_async(payload)
    claim_task_access(db, task_id=accepted.task_id, user_id=current_user.id, module="cpra")
    return accepted


@router.get("/tasks/{task_id}", response_model=CPRAAsyncStatus)
def get_cpra_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> CPRAAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="cpra",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry", response_model=CPRAAsyncStatus)
def retry_cpra_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> CPRAAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
