from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.services.task_access import claim_task_access, require_task_access
from backend.services.runtime_health import require_healthy_llm
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.domains.us.eo14117_flow_review.schema import (
    CNFlowAsyncAccepted,
    CNFlowAsyncStatus,
    CNFlowRequest,
    CNFlowResult,
)
from backend.domains.us.eo14117_flow_review.service import CNFlowService

router = APIRouter(prefix="/cn-flow", tags=["cn-flow"])
service = CNFlowService()


@router.post("/generate", response_model=CNFlowResult, dependencies=[Depends(require_healthy_llm)])
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


@router.post("/generate_async", response_model=CNFlowAsyncAccepted, dependencies=[Depends(require_healthy_llm)])
def generate_cn_flow_async(
    payload: CNFlowRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> CNFlowAsyncAccepted:
    accepted = service.submit_async(payload)
    claim_task_access(db, task_id=accepted.task_id, user_id=current_user.id, module="cn_flow")
    return accepted


@router.get("/tasks/{task_id}", response_model=CNFlowAsyncStatus)
def get_cn_flow_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> CNFlowAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
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


@router.post("/tasks/{task_id}/retry", response_model=CNFlowAsyncStatus)
def retry_cn_flow_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> CNFlowAsyncStatus:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
