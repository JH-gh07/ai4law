from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.domains.cn.scc_review.schema import SCCAsyncAccepted, SCCAsyncStatus, SCCRequest, SCCResult
from backend.domains.cn.scc_review.service import SCCService

router = APIRouter(prefix="/scc", tags=["scc"])
service = SCCService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/generate", response_model=SCCResult)
def generate_scc(
    payload: SCCRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> SCCResult:
    result = trace_sync("scc", lambda: service.generate_report(payload))
    register_module_result_artifacts(
        db=db,
        container=container,
        user=current_user,
        module_key="scc",
        result=result,
    )
    return result


@router.post("/generate_async", response_model=SCCAsyncAccepted)
def generate_scc_async(
    payload: SCCRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> SCCAsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/tasks/{task_id}", response_model=SCCAsyncStatus)
def get_scc_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> SCCAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="scc",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry", response_model=SCCAsyncStatus)
def retry_scc_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> SCCAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
