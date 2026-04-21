from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user, get_db
from backend.core.json_utils import dumps, loads
from backend.models.workspace import WorkspaceStateModel
from backend.schemas.auth import AuthUser
from backend.schemas.workspace import WorkspaceStatePayload, WorkspaceStateResponse

router = APIRouter()


def _normalize_payload(raw: dict) -> WorkspaceStatePayload:
    return WorkspaceStatePayload(
        task_spaces=raw.get("task_spaces") if isinstance(raw.get("task_spaces"), list) else [],
        module_runs=raw.get("module_runs") if isinstance(raw.get("module_runs"), list) else [],
        artifacts=raw.get("artifacts") if isinstance(raw.get("artifacts"), list) else [],
        evidence_hits=raw.get("evidence_hits") if isinstance(raw.get("evidence_hits"), list) else [],
        issues=raw.get("issues") if isinstance(raw.get("issues"), list) else [],
    )


@router.get("", response_model=WorkspaceStateResponse)
def get_workspace_state(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    stmt = select(WorkspaceStateModel).where(WorkspaceStateModel.user_id == current_user.id)
    row = db.scalars(stmt).first()
    if not row:
        return WorkspaceStateResponse(state=WorkspaceStatePayload(), updated_at=datetime.now(timezone.utc))

    payload = _normalize_payload(loads(row.state_json, {}))
    return WorkspaceStateResponse(state=payload, updated_at=row.updated_at)


@router.put("", response_model=WorkspaceStateResponse)
def upsert_workspace_state(
    payload: WorkspaceStatePayload,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    stmt = select(WorkspaceStateModel).where(WorkspaceStateModel.user_id == current_user.id)
    row = db.scalars(stmt).first()
    if not row:
        row = WorkspaceStateModel(user_id=current_user.id, state_json=dumps(payload.model_dump()))
        db.add(row)
    else:
        row.state_json = dumps(payload.model_dump())
    db.commit()
    db.refresh(row)
    return WorkspaceStateResponse(state=payload, updated_at=row.updated_at)
