from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.domains.cn.security_assessment.schema import (
    AssessmentAsyncAccepted,
    AssessmentAsyncStatus,
    AssessmentRequest,
    AssessmentResult,
)
from backend.domains.cn.security_assessment.service import AssessmentService

router = APIRouter(prefix="/assessment", tags=["assessment"])
service = AssessmentService()
TASK_OWNERS: dict[str, str] = {}


def _assert_owner(task_id: str, user_id: str) -> None:
    owner = TASK_OWNERS.get(task_id)
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/generate", response_model=AssessmentResult)
def generate_assessment(
    payload: AssessmentRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> AssessmentResult:
    try:
        result = trace_sync("assessment", lambda: service.generate_report(payload))
        register_module_result_artifacts(
            db=db,
            container=container,
            user=current_user,
            module_key="assessment",
            result=result,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate_async", response_model=AssessmentAsyncAccepted)
def generate_assessment_async(
    payload: AssessmentRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> AssessmentAsyncAccepted:
    try:
        accepted = service.submit_async(payload)
        TASK_OWNERS[accepted.task_id] = current_user.id
        return accepted
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=AssessmentAsyncStatus)
def get_assessment_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> AssessmentAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        status = service.get_async_status(task_id)
        result = getattr(status, "result", None)
        if result is not None:
            register_module_result_artifacts(
                db=db,
                container=container,
                user=current_user,
                module_key="assessment",
                result=result,
            )
        return status
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry", response_model=AssessmentAsyncStatus)
def retry_assessment_task(
    task_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> AssessmentAsyncStatus:
    _assert_owner(task_id, current_user.id)
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
