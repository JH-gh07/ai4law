from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.dependencies import get_container, get_db
from backend.schemas.diagnosis import (
    AssessmentHandoffResponse,
    ComplianceProfileDraft,
    ComplianceQuestionnaire,
    DiagnosisAnswerSet,
    DiagnosisContextResponse,
    DiagnosisReportResponse,
    DiagnosisSessionCreateResponse,
    DiagnosisSessionResponse,
    SCCHandoffResponse,
)

router = APIRouter()


@router.post("/sessions", response_model=DiagnosisSessionCreateResponse)
def create_session(
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    return container.diagnosis_service.create_session(db)


@router.put("/sessions/{session_id}/questionnaire", response_model=DiagnosisSessionResponse)
def submit_questionnaire(
    session_id: str,
    questionnaire: ComplianceQuestionnaire,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.submit_questionnaire(db, session_id, questionnaire)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post("/sessions/{session_id}/evaluate", response_model=DiagnosisSessionResponse)
def evaluate_questionnaire(
    session_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.evaluate_questionnaire(db, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.put("/sessions/{session_id}/answers", response_model=DiagnosisSessionResponse)
def submit_answers_compat(
    session_id: str,
    answers: DiagnosisAnswerSet,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.submit_answers(db, session_id, answers)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/sessions/{session_id}/profile", response_model=ComplianceProfileDraft)
def get_profile(
    session_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_profile(db, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/sessions/{session_id}/result", response_model=DiagnosisSessionResponse)
def get_result(
    session_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_result(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/report", response_model=DiagnosisReportResponse)
def generate_report(
    session_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.generate_report(db, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/sessions/{session_id}/context", response_model=DiagnosisContextResponse)
def get_context(
    session_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_context(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/handoff/assessment", response_model=AssessmentHandoffResponse)
def get_assessment_handoff(
    session_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_assessment_handoff(db, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/sessions/{session_id}/handoff/scc", response_model=SCCHandoffResponse)
def get_scc_handoff(
    session_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    try:
        return container.diagnosis_service.get_scc_handoff(db, session_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc
