import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user, get_db
from backend.repositories.report_repository import ReportRepository
from backend.schemas.auth import AuthUser
from backend.schemas.me import ReportMetadataResponse

router = APIRouter()
_repo = ReportRepository()


@router.get("/{owner_id}/metadata", response_model=ReportMetadataResponse)
def get_report_metadata(
    owner_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    rows = _repo.list_by_user_and_owner(db, current_user.id, owner_id)
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
