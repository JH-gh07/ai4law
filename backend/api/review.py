from fastapi import APIRouter, Depends, File, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.core.dependencies import get_container, get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.schemas.review import (
    ReviewAnalyzeResponse,
    ReviewAsyncAccepted,
    ReviewAsyncStatus,
    ReviewGenerateRequest,
    ReviewGenerateResponse,
    ReviewIssuesResponse,
    ReviewReportResponse,
    ReviewTaskCreateResponse,
    ReviewTaskStatusResponse,
    UploadedFileResponse,
)

router = APIRouter()


@router.post("/generate", response_model=ReviewGenerateResponse)
def generate_review(
    payload: ReviewGenerateRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.generate_from_uploaded_paths(db, current_user.id, payload.uploaded_files)


@router.post("/generate_async", response_model=ReviewAsyncAccepted)
def generate_review_async(
    payload: ReviewGenerateRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.submit_async_from_uploaded_paths(db, current_user.id, payload.uploaded_files)


@router.get("/tasks/{task_id}", response_model=ReviewAsyncStatus)
def get_review_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.get_async_status(db, current_user.id, task_id)


@router.post("/tasks", response_model=ReviewTaskCreateResponse)
def create_task(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.create_task(db, current_user.id)


@router.post("/tasks/{task_id}/files", response_model=UploadedFileResponse)
def upload_file(
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.upload_file(db, current_user.id, task_id, file)


@router.post("/tasks/{task_id}/analyze", response_model=ReviewAnalyzeResponse)
def analyze_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.analyze(db, current_user.id, task_id)


@router.get("/tasks/{task_id}/status", response_model=ReviewTaskStatusResponse)
def get_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.get_status(db, current_user.id, task_id)


@router.get("/tasks/{task_id}/issues", response_model=ReviewIssuesResponse)
def get_issues(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.get_issues(db, current_user.id, task_id)


@router.get("/tasks/{task_id}/report", response_model=ReviewReportResponse)
def get_report(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    return container.review_service.get_report(db, current_user.id, task_id)


@router.websocket("/ws/tasks/{task_id}")
async def review_updates(websocket: WebSocket, task_id: str):
    manager = websocket.app.state.container.websocket_manager
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
