import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user, get_db
from backend.repositories.diagnosis_repository import DiagnosisRepository
from backend.repositories.report_repository import ReportRepository
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.auth import AuthUser
from backend.schemas.me import (
    MyReportItem,
    MyReportsResponse,
    MyTaskItem,
    MyTasksResponse,
    ReportMetadataResponse,
)

router = APIRouter()
_diagnosis_repo = DiagnosisRepository()
_review_repo = ReviewRepository()
_report_repo = ReportRepository()


@router.get("/tasks", response_model=MyTasksResponse)
def list_my_tasks(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    diagnosis_rows = _diagnosis_repo.list_by_user(db, current_user.id)
    review_rows = _review_repo.list_tasks_by_user(db, current_user.id)

    items: list[MyTaskItem] = []
    for row in diagnosis_rows:
        items.append(
            MyTaskItem(
                id=row.id,
                source="diagnosis",
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
                module="diagnosis",
            )
        )

    for row in review_rows:
        items.append(
            MyTaskItem(
                id=row.id,
                source="review",
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
                module="review",
            )
        )

    items.sort(key=lambda item: item.updated_at, reverse=True)
    return MyTasksResponse(items=items)


@router.get("/reports", response_model=MyReportsResponse)
def list_my_reports(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    rows = _report_repo.list_by_user(db, current_user.id)
    return MyReportsResponse(
        items=[
            MyReportItem(
                id=row.id,
                owner_type=row.owner_type,
                owner_id=row.owner_id,
                artifact_type=row.artifact_type,
                file_path=row.file_path,
                created_at=row.created_at,
                preview=(row.preview_json and json.loads(row.preview_json)) or {},
            )
            for row in rows
        ]
    )


@router.get("/reports/{owner_id}/metadata", response_model=ReportMetadataResponse)
def get_report_metadata(
    owner_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    rows = _report_repo.list_by_user_and_owner(db, current_user.id, owner_id)
    latest = rows[0] if rows else None
    preview = {}
    if latest and latest.preview_json:
        try:
            preview = json.loads(latest.preview_json)
        except Exception:  # noqa: BLE001
            preview = {}
    return ReportMetadataResponse(
        owner_id=owner_id,
        version=f"Draft-{(latest.created_at.isoformat()[:10].replace('-', '')) if latest else 'NA'}",
        risk_level=preview.get("risk_level") if isinstance(preview, dict) else None,
        summary=preview.get("summary") if isinstance(preview, dict) else None,
    )
