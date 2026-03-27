from fastapi import APIRouter, Depends, File, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.core.dependencies import get_container, get_db
from backend.schemas.review import (
    ReviewAnalyzeResponse,
    ReviewIssuesResponse,
    ReviewReportResponse,
    ReviewTaskCreateResponse,
    ReviewTaskStatusResponse,
    UploadedFileResponse,
)

router = APIRouter()


@router.post("/tasks", response_model=ReviewTaskCreateResponse)
def create_task(
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    return container.review_service.create_task(db)


@router.post("/tasks/{task_id}/files", response_model=UploadedFileResponse)
def upload_file(
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    return container.review_service.upload_file(db, task_id, file)


@router.post("/tasks/{task_id}/analyze", response_model=ReviewAnalyzeResponse)
def analyze_task(
    task_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    return container.review_service.analyze(db, task_id)


@router.get("/tasks/{task_id}/status", response_model=ReviewTaskStatusResponse)
def get_status(
    task_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    return container.review_service.get_status(db, task_id)


@router.get("/tasks/{task_id}/issues", response_model=ReviewIssuesResponse)
def get_issues(
    task_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    return container.review_service.get_issues(db, task_id)


@router.get("/tasks/{task_id}/report", response_model=ReviewReportResponse)
def get_report(
    task_id: str,
    db: Session = Depends(get_db),
    container=Depends(get_container),
):
    return container.review_service.get_report(db, task_id)


@router.websocket("/ws/tasks/{task_id}")
async def review_updates(websocket: WebSocket, task_id: str):
    manager = websocket.app.state.container.websocket_manager
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
