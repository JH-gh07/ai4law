from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.modules.cn_flow.schema import (
    CNFlowAsyncAccepted,
    CNFlowAsyncStatus,
    CNFlowRequest,
    CNFlowResult,
)
from backend.modules.cn_flow.service import CNFlowService

router = APIRouter(tags=["cn-flow"])
service = CNFlowService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/cn-flow/generate", response_model=CNFlowResult)
def generate_cn_flow(
    payload: CNFlowRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> CNFlowResult:
    result = trace_sync("cn_flow", lambda: service.generate_report(payload))
    register_module_result_artifacts(
        db=db,
        container=container,
        user=current_user,
        module_key="cn_flow",
        result=result,
    )
    return result


@router.post("/cn-flow/generate_async", response_model=CNFlowAsyncAccepted)
def generate_cn_flow_async(
    payload: CNFlowRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> CNFlowAsyncAccepted:
    accepted = service.submit_async(payload)
    TASK_OWNERS[accepted.task_id] = current_user.id
    return accepted


@router.get("/cn-flow/tasks/{task_id}", response_model=CNFlowAsyncStatus)
def get_cn_flow_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> CNFlowAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="cn_flow",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cn-flow/tasks/{task_id}/retry", response_model=CNFlowAsyncStatus)
def retry_cn_flow_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> CNFlowAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
