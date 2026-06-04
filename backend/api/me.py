import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.common.events.manager import get_ssemanager
from backend.core.dependencies import get_current_user, get_db
from backend.core.json_utils import dumps, loads
from backend.models.diagnosis import DiagnosisSessionModel
from backend.models.report import ReportArtifactModel
from backend.models.review import ReviewTaskModel, UploadedFileModel
from backend.models.workspace import WorkspaceStateModel
from backend.repositories.diagnosis_repository import DiagnosisRepository
from backend.repositories.report_repository import ReportRepository
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.auth import AuthUser
from backend.schemas.me import (
    DeleteProjectHistoryResponse,
    MyReportItem,
    MyReportsResponse,
    MyTaskItem,
    MyTasksResponse,
    ReportMetadataResponse,
    RecoveredModuleRun,
    RecoveredWorkspaceItem,
    RecoveredWorkspaceResponse,
)

router = APIRouter()
_diagnosis_repo = DiagnosisRepository()
_review_repo = ReviewRepository()
_report_repo = ReportRepository()

_KNOWN_MODULES = {
    "diagnosis",
    "review",
    "assessment",
    "dpia",
    "scc",
    "cn_flow",
    "eu_scc",
    "us_14117",
    "pipia",
    "tia",
    "bcr",
    "cpra",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()


def _safe_remove_path(path: Path) -> bool:
    try:
        if not path.exists() and not path.is_symlink():
            return False
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        return True
    except Exception:  # noqa: BLE001
        return False


def _find_task_root_from_path(path: Path, task_id: str) -> Path | None:
    resolved = path.resolve()
    for parent in resolved.parents:
        if parent.name == task_id:
            return parent
    return None


def _prune_workspace_state(raw_state: dict[str, Any], task_id: str) -> tuple[dict[str, Any], dict[str, int]]:
    counts = {
        "deleted_task_spaces": 0,
        "deleted_module_runs": 0,
        "deleted_artifacts": 0,
        "deleted_evidence_hits": 0,
        "deleted_issues": 0,
    }
    key_map = {
        "task_spaces": ("id", "deleted_task_spaces"),
        "module_runs": ("taskSpaceId", "deleted_module_runs"),
        "artifacts": ("taskSpaceId", "deleted_artifacts"),
        "evidence_hits": ("taskSpaceId", "deleted_evidence_hits"),
        "issues": ("taskSpaceId", "deleted_issues"),
    }

    next_state = dict(raw_state)
    for field, (id_key, count_key) in key_map.items():
        raw_items = raw_state.get(field)
        if not isinstance(raw_items, list):
            next_state[field] = []
            continue
        kept_items = []
        removed = 0
        for item in raw_items:
            if isinstance(item, dict) and item.get(id_key) == task_id:
                removed += 1
                continue
            kept_items.append(item)
        next_state[field] = kept_items
        counts[count_key] = removed
    return next_state, counts


def _extract_output_files(artifacts: list[MyReportItem]) -> dict[str, str]:
    output_files: dict[str, str] = {}
    for artifact in artifacts:
        if artifact.artifact_type and artifact.file_path:
            output_files[artifact.artifact_type] = artifact.file_path
    return output_files


def _reconstruct_response(module: str, task_id: str, artifacts: list[MyReportItem]) -> dict[str, Any] | None:
    output_dir = Path("outputs") / module / task_id / "outputs"
    if not output_dir.exists():
        for artifact in artifacts:
            artifact_path = _resolve_path(artifact.file_path)
            parent = artifact_path.parent
            if parent.exists():
                output_dir = parent
                break
    response: dict[str, Any] = {
        "task_id": task_id,
        "output_files": _extract_output_files(artifacts),
    }

    markdown_candidates = sorted(output_dir.glob("*.md"))
    if markdown_candidates:
        markdown = _read_text(markdown_candidates[0])
        if markdown:
            response["chapters"] = [{"title": markdown_candidates[0].stem, "content": markdown}]

    for candidate in sorted(output_dir.glob("*.json")):
        data = _read_json(candidate)
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("chapters"), list):
            response["chapters"] = data["chapters"]
        if isinstance(data.get("consistency_issues"), list):
            response["consistency_issues"] = data["consistency_issues"]
        if isinstance(data.get("regulations"), list):
            response["regulations"] = data["regulations"]
        if candidate.name == "citation_map.json":
            response["citation_map_path"] = str(candidate.resolve())

    if len(response) <= 2:
        return None
    return response


def _build_recovered_run(task: MyTaskItem, artifacts: list[MyReportItem]) -> RecoveredModuleRun:
    module = task.module or task.source
    normalized_status = task.status.lower()
    terminal_states = {"completed", "succeeded", "failed", "canceled", "cancelled"}
    success_states = {"completed", "succeeded"}
    response = _reconstruct_response(module, task.id, artifacts)
    return RecoveredModuleRun(
        id=f"{module}:{task.id}",
        task_space_id=task.id,
        module=module,
        run_mode="async",
        started_at=task.created_at,
        finished_at=task.updated_at if normalized_status in terminal_states else None,
        success=normalized_status in success_states,
        request={},
        response=response,
        error=None if normalized_status in success_states or normalized_status in {"created", "running"} else task.status,
        async_task_id=task.id,
        async_state=normalized_status,
    )


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


@router.get("/workspace-recovery", response_model=RecoveredWorkspaceResponse)
def get_workspace_recovery(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    tasks = list_my_tasks(db=db, current_user=current_user).items
    reports = list_my_reports(db=db, current_user=current_user).items

    reports_by_owner: dict[tuple[str, str], list[MyReportItem]] = {}
    for report in reports:
        reports_by_owner.setdefault((report.owner_type, report.owner_id), []).append(report)

    recovered_items: list[RecoveredWorkspaceItem] = []
    seen_keys: set[tuple[str, str]] = set()

    for task in tasks:
        module = task.module or task.source
        key = (module, task.id)
        seen_keys.add(key)
        artifacts = reports_by_owner.get(key, [])
        recovered_items.append(
            RecoveredWorkspaceItem(
                task_id=task.id,
                module=module,
                status=task.status,
                created_at=task.created_at,
                updated_at=task.updated_at,
                run=_build_recovered_run(task, artifacts),
                artifacts=artifacts,
            )
        )

    for report in reports:
        key = (report.owner_type, report.owner_id)
        if key in seen_keys or report.owner_type not in _KNOWN_MODULES:
            continue
        owner_id = report.owner_id
        if not owner_id:
            continue
        artifacts = reports_by_owner.get(key, [report])
        response = _reconstruct_response(report.owner_type, owner_id, artifacts)
        recovered_items.append(
            RecoveredWorkspaceItem(
                task_id=owner_id,
                module=report.owner_type,
                status="completed" if response else "unknown",
                created_at=report.created_at,
                updated_at=report.created_at,
                run=RecoveredModuleRun(
                    id=f"{report.owner_type}:{owner_id}",
                    task_space_id=owner_id,
                    module=report.owner_type,
                    run_mode="async",
                    started_at=report.created_at,
                    finished_at=report.created_at,
                    success=response is not None,
                    request={},
                    response=response,
                    error=None,
                    async_task_id=owner_id,
                    async_state="completed" if response else "unknown",
                ),
                artifacts=artifacts,
            )
        )

    recovered_items.sort(key=lambda item: item.updated_at, reverse=True)
    return RecoveredWorkspaceResponse(items=recovered_items)


@router.delete("/projects/{task_id}", response_model=DeleteProjectHistoryResponse)
def delete_project_history(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    if not task_id.strip():
        raise HTTPException(status_code=400, detail="task_id is required")

    deleted_paths: list[str] = []
    seen_paths: set[str] = set()

    diagnosis_rows = list(
        db.scalars(
            select(DiagnosisSessionModel).where(
                DiagnosisSessionModel.id == task_id,
                DiagnosisSessionModel.user_id == current_user.id,
            )
        )
    )
    review_rows = list(
        db.scalars(
            select(ReviewTaskModel).where(
                ReviewTaskModel.id == task_id,
                ReviewTaskModel.user_id == current_user.id,
            )
        )
    )
    uploaded_rows = list(
        db.scalars(
            select(UploadedFileModel).where(
                UploadedFileModel.task_id == task_id,
                UploadedFileModel.user_id == current_user.id,
            )
        )
    )
    report_rows = list(
        db.scalars(
            select(ReportArtifactModel).where(
                ReportArtifactModel.owner_id == task_id,
                ReportArtifactModel.user_id == current_user.id,
            )
        )
    )

    workspace_row = db.scalars(
        select(WorkspaceStateModel).where(WorkspaceStateModel.user_id == current_user.id)
    ).first()
    workspace_counts = {
        "deleted_task_spaces": 0,
        "deleted_module_runs": 0,
        "deleted_artifacts": 0,
        "deleted_evidence_hits": 0,
        "deleted_issues": 0,
    }
    if workspace_row:
        raw_state = loads(workspace_row.state_json, {})
        if not isinstance(raw_state, dict):
            raw_state = {}
        next_state, workspace_counts = _prune_workspace_state(raw_state, task_id)
        workspace_row.state_json = dumps(next_state)

    owned_modules = {
        row.owner_type
        for row in report_rows
        if isinstance(row.owner_type, str) and row.owner_type
    }
    if diagnosis_rows:
        owned_modules.add("diagnosis")
    if review_rows:
        owned_modules.add("review")

    for row in uploaded_rows:
        resolved = _resolve_path(row.storage_path)
        if str(resolved) not in seen_paths and _safe_remove_path(resolved):
            seen_paths.add(str(resolved))
            deleted_paths.append(str(resolved))
        db.delete(row)

    report_parent_dirs: set[Path] = set()
    task_root_dirs: set[Path] = set()
    for row in report_rows:
        resolved = _resolve_path(row.file_path)
        report_parent_dirs.add(resolved.parent)
        task_root = _find_task_root_from_path(resolved, task_id)
        if task_root:
            task_root_dirs.add(task_root)
        if str(resolved) not in seen_paths and _safe_remove_path(resolved):
            seen_paths.add(str(resolved))
            deleted_paths.append(str(resolved))
        db.delete(row)

    for row in diagnosis_rows:
        db.delete(row)
    for row in review_rows:
        db.delete(row)

    settings = request.app.state.container.settings
    for module in sorted(owned_modules):
        output_dir = (Path.cwd() / "outputs" / module / task_id).resolve()
        if str(output_dir) not in seen_paths and _safe_remove_path(output_dir):
            seen_paths.add(str(output_dir))
            deleted_paths.append(str(output_dir))

        report_dir = (settings.report_dir / module / task_id).resolve()
        if str(report_dir) not in seen_paths and _safe_remove_path(report_dir):
            seen_paths.add(str(report_dir))
            deleted_paths.append(str(report_dir))

    for task_root in task_root_dirs:
        resolved_root = task_root.resolve()
        if str(resolved_root) not in seen_paths and _safe_remove_path(resolved_root):
            seen_paths.add(str(resolved_root))
            deleted_paths.append(str(resolved_root))

    for parent in report_parent_dirs:
        if parent.name == task_id and str(parent.resolve()) not in seen_paths and _safe_remove_path(parent.resolve()):
            seen_paths.add(str(parent.resolve()))
            deleted_paths.append(str(parent.resolve()))

    db.commit()
    get_ssemanager().clear_task(task_id)

    return DeleteProjectHistoryResponse(
        task_id=task_id,
        deleted_task_spaces=workspace_counts["deleted_task_spaces"],
        deleted_module_runs=workspace_counts["deleted_module_runs"],
        deleted_artifacts=workspace_counts["deleted_artifacts"],
        deleted_evidence_hits=workspace_counts["deleted_evidence_hits"],
        deleted_issues=workspace_counts["deleted_issues"],
        deleted_diagnosis_sessions=len(diagnosis_rows),
        deleted_review_tasks=len(review_rows),
        deleted_uploaded_files=len(uploaded_rows),
        deleted_report_records=len(report_rows),
        deleted_paths=deleted_paths,
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
