from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.artifact_registry import register_module_result_artifacts
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.common.trace.tracer import trace_sync
from backend.modules.cpra.schema import CPRAAsyncAccepted, CPRAAsyncStatus, CPRARequest, CPRAResult
from backend.modules.cpra.service import CPRAService

router = APIRouter(tags=["cpra"])
service = CPRAService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/cpra/generate", response_model=CPRAResult)
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


@router.post("/cpra/generate_async", response_model=CPRAAsyncAccepted)
def generate_cpra_async(
    payload: CPRARequest,
    current_user: AuthUser = Depends(get_current_user),
) -> CPRAAsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/cpra/tasks/{task_id}", response_model=CPRAAsyncStatus)
def get_cpra_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> CPRAAsyncStatus:
    _assert_owner(task_id, current_user.id)
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


@router.post("/cpra/tasks/{task_id}/retry", response_model=CPRAAsyncStatus)
def retry_cpra_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> CPRAAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
