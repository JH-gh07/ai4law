"""EU SCC API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.modules.eu_scc.schema import SCCAsyncAccepted, SCCAsyncStatus, SCCReviewRequest, SCCReviewResult
from backend.modules.eu_scc.service import EU_SCCService

router = APIRouter(prefix="/eu_scc", tags=["eu_scc"])
service = EU_SCCService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    if TASK_OWNERS.get(task_id, user_id) != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/generate", response_model=SCCReviewResult)
def generate_eu_scc(payload: SCCReviewRequest, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user), container=Depends(get_container)) -> SCCReviewResult:
    result = trace_sync("eu_scc", lambda: service.generate_report(payload))
    register_module_result_artifacts(db=db, container=container, user=current_user, module_key="eu_scc", result=result)
    return result


@router.post("/generate_async", response_model=SCCAsyncAccepted)
def generate_eu_scc_async(payload: SCCReviewRequest, current_user: AuthUser = Depends(get_current_user)) -> SCCAsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/tasks/{task_id}", response_model=SCCAsyncStatus)
def get_eu_scc_task(task_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user), container=Depends(get_container)) -> SCCAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        if getattr(status, "result", None):
            register_module_result_artifacts(db=db, container=container, user=current_user, module_key="eu_scc", result=status.result)
        return status
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/tasks/{task_id}/retry", response_model=SCCAsyncStatus)
def retry_eu_scc_task(task_id: str, current_user: AuthUser = Depends(get_current_user)) -> SCCAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
