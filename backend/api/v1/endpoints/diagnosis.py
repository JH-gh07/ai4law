from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.schemas.diagnosis import (
    AssessmentHandoffResponse,
    DiagnosisAnswerSet,
    DiagnosisContextResponse,
    DiagnosisReportResponse,
    PIPIAHandoffResponse,
    DiagnosisSessionCreateResponse,
    DiagnosisSessionResponse,
)

router = APIRouter()


@router.post("/sessions", response_model=DiagnosisSessionCreateResponse)
def create_session(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.diagnosis_service.create_session(db, current_user.id)


@router.put("/sessions/{session_id}/answers", response_model=DiagnosisSessionResponse)
def submit_answers(
    session_id: str,
    answers: DiagnosisAnswerSet,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.submit_answers(db, current_user.id, session_id, answers)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/result", response_model=DiagnosisSessionResponse)
def get_result(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_result(db, current_user.id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/report", response_model=DiagnosisReportResponse)
def generate_report(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.generate_report(db, current_user.id, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/sessions/{session_id}/context", response_model=DiagnosisContextResponse)
def get_context(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_context(db, current_user.id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/handoff/assessment", response_model=AssessmentHandoffResponse)
def get_assessment_handoff(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_assessment_handoff(db, current_user.id, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/sessions/{session_id}/handoff/pipia", response_model=PIPIAHandoffResponse)
def get_pipia_handoff(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_pipia_handoff(db, current_user.id, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc
