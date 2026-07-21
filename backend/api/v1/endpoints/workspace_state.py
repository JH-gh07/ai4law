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


def _is_retired_cn_scc_task(item: dict) -> bool:
    if item.get("taskTemplateId") == "cn_scc":
        return True
    if item.get("module") == "scc" or item.get("workspaceStyle") == "cn_scc":
        return True
    return (
        str(item.get("name", "")).startswith("中国标准合同审查")
        and item.get("taskTemplateId") == "cn_diagnosis"
        and item.get("module") == "diagnosis"
    )


def _normalize_payload(raw: dict) -> WorkspaceStatePayload:
    task_spaces = (
        raw.get("task_spaces")
        if isinstance(raw.get("task_spaces"), list)
        else []
    )
    retired_task_ids = {
        str(item.get("id"))
        for item in task_spaces
        if isinstance(item, dict) and _is_retired_cn_scc_task(item)
    }

    def active_items(field: str) -> list[dict]:
        items = raw.get(field) if isinstance(raw.get(field), list) else []
        return [
            item
            for item in items
            if isinstance(item, dict)
            and item.get("module") != "scc"
            and item.get("taskSpaceId") not in retired_task_ids
        ]

    return WorkspaceStatePayload(
        task_spaces=[
            item
            for item in task_spaces
            if isinstance(item, dict) and not _is_retired_cn_scc_task(item)
        ],
        module_runs=active_items("module_runs"),
        artifacts=active_items("artifacts"),
        evidence_hits=active_items("evidence_hits"),
        issues=active_items("issues"),
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
    normalized = _normalize_payload(payload.model_dump())
    stmt = select(WorkspaceStateModel).where(WorkspaceStateModel.user_id == current_user.id)
    row = db.scalars(stmt).first()
    if not row:
        row = WorkspaceStateModel(user_id=current_user.id, state_json=dumps(normalized.model_dump()))
        db.add(row)
    else:
        row.state_json = dumps(normalized.model_dump())
    db.commit()
    db.refresh(row)
    return WorkspaceStateResponse(state=normalized, updated_at=row.updated_at)
