from fastapi import APIRouter, HTTPException

from backend.modules.assessment.schema import (
    AssessmentAsyncAccepted,
    AssessmentAsyncStatus,
    AssessmentRequest,
    AssessmentResult,
)
from backend.modules.assessment.service import AssessmentService

router = APIRouter(tags=["assessment"])
service = AssessmentService()


@router.post("/assessment/generate", response_model=AssessmentResult)
def generate_assessment(payload: AssessmentRequest) -> AssessmentResult:
    try:
        return service.generate_report(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/assessment/generate_async", response_model=AssessmentAsyncAccepted)
def generate_assessment_async(payload: AssessmentRequest) -> AssessmentAsyncAccepted:
    try:
        return service.submit_async(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/assessment/tasks/{task_id}", response_model=AssessmentAsyncStatus)
def get_assessment_task(task_id: str) -> AssessmentAsyncStatus:
    try:
        return service.get_async_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/assessment/tasks/{task_id}/retry", response_model=AssessmentAsyncStatus)
def retry_assessment_task(task_id: str) -> AssessmentAsyncStatus:
    try:
        return service.retry_async(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
