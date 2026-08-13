import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.common.reporting import DocumentIR, migrate_v3_document
from backend.common.storage.file_parser import FileParser
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.models.report import ReportArtifactModel
from backend.models.review import UploadedFileModel
from backend.schemas.auth import AuthUser
from backend.schemas.common import ArtifactPreviewResponse

_DOCUMENT_IR_ARTIFACT_TYPE = "document_ir_json"

router = APIRouter()


def _artifact_root_aliases(container) -> list[tuple[Path, Path]]:
    """Return each configured artifact root as logical and physical paths."""
    cwd = Path.cwd().resolve()
    logical_roots = [
        Path("outputs"),
        container.settings.storage_dir,
        container.settings.report_dir,
        container.settings.upload_dir,
    ]
    aliases: list[tuple[Path, Path]] = []
    for logical in logical_roots:
        logical_absolute = logical if logical.is_absolute() else cwd / logical
        aliases.append((logical, logical_absolute.resolve()))
    return aliases


def _allowed_roots(container) -> list[Path]:
    return list(dict.fromkeys(physical for _, physical in _artifact_root_aliases(container)))


def _resolve_artifact_path(raw_path: str, container) -> Path:
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found.")

    for root in _allowed_roots(container):
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue

    raise HTTPException(status_code=403, detail="Artifact path is outside allowed preview scope.")


def _add_path_variants(candidates: set[str], path: Path) -> None:
    value = path.as_posix()
    candidates.update({str(path), value})
    if not path.is_absolute():
        candidates.add(f"./{value}")


def _candidate_artifact_paths(resolved: Path, container) -> set[str]:
    candidates = {str(resolved), resolved.as_posix()}
    cwd = Path.cwd().resolve()
    try:
        relative = resolved.relative_to(cwd)
    except ValueError:
        relative = None

    if relative is not None:
        _add_path_variants(candidates, relative)

    for logical_root, physical_root in _artifact_root_aliases(container):
        try:
            suffix = resolved.relative_to(physical_root)
        except ValueError:
            continue
        logical_path = logical_root / suffix
        _add_path_variants(candidates, logical_path)
        logical_absolute = logical_path if logical_path.is_absolute() else cwd / logical_path
        _add_path_variants(candidates, logical_absolute)

    return {item for item in candidates if item}


def _resolve_artifact_access(db: Session, user: AuthUser, resolved: Path, container) -> str | None:
    """Return the registered ``artifact_type`` of a user-owned report artifact.

    ``None`` means the path is authorized via a user-owned *upload* (which has
    no report artifact type). Raises 403 when the path is neither a user-owned
    report artifact nor a user-owned upload.
    """
    candidate_paths = tuple(_candidate_artifact_paths(resolved, container))
    report_stmt = select(ReportArtifactModel.artifact_type).where(
        ReportArtifactModel.user_id == user.id,
        ReportArtifactModel.file_path.in_(candidate_paths),
    )
    report_type = db.execute(report_stmt).scalars().first()
    if report_type is not None:
        return report_type
    upload_stmt = select(UploadedFileModel.id).where(
        UploadedFileModel.user_id == user.id,
        UploadedFileModel.storage_path.in_(candidate_paths),
    )
    upload_hit = db.execute(upload_stmt).scalar_one_or_none()
    if upload_hit:
        return None
    raise HTTPException(status_code=403, detail="You do not have access to this artifact.")


def _parse_document_ir(raw_text: str) -> dict:
    """Validate a document IR payload, returning the canonical v4 dict.

    Raises 422 for corrupted JSON, non-object payloads, unknown schema
    versions, or Pydantic validation failures. Accepts both explicit v4
    (``schema_version == "4.0"``) and v3 (migrated via ``migrate_v3_document``).
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Corrupted document IR: invalid JSON ({exc.msg})",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=422,
            detail="Corrupted document IR: top-level value must be an object",
        )

    schema_version = data.get("schema_version")
    try:
        if schema_version == "4.0":
            document = DocumentIR.model_validate(data)
        elif schema_version == "3.0":
            document = migrate_v3_document(data)
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown DocumentIR schema version: {schema_version!r}",
            )
    except HTTPException:
        raise
    except (ValidationError, ValueError, KeyError) as exc:
        detail = exc.errors() if isinstance(exc, ValidationError) else str(exc)
        raise HTTPException(
            status_code=422,
            detail=f"Corrupted document IR: {detail}",
        ) from exc
    return document.model_dump(mode="json")


@router.get("/preview", response_model=ArtifactPreviewResponse)
def preview_artifact(
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    resolved = _resolve_artifact_path(path, container)
    artifact_type = _resolve_artifact_access(db, current_user, resolved, container)
    suffix = resolved.suffix.lower()
    parser = FileParser()
    file_url = f"/api/v1/artifacts/file?path={quote(str(resolved))}"

    # Structured report body: only a *registered* document IR artifact that
    # passes validation may expose ``report_ir``. Structured content never
    # shares the raw-text ``content`` field.
    if artifact_type == _DOCUMENT_IR_ARTIFACT_TYPE:
        report_ir = _parse_document_ir(resolved.read_text(encoding="utf-8"))
        return ArtifactPreviewResponse(
            path=str(resolved),
            file_name=resolved.name,
            kind=_DOCUMENT_IR_ARTIFACT_TYPE,
            render_mode="report_ir",
            content="",
            file_url=file_url,
            report_ir=report_ir,
        )

    if suffix == ".html":
        raw_html = resolved.read_text(encoding="utf-8", errors="ignore")
        return ArtifactPreviewResponse(
            path=str(resolved),
            file_name=resolved.name,
            kind=suffix.lstrip(".") or "file",
            render_mode="html",
            content=raw_html,
            file_url=file_url,
        )

    if suffix == ".pdf":
        return ArtifactPreviewResponse(
            path=str(resolved),
            file_name=resolved.name,
            kind="pdf",
            render_mode="pdf",
            content=parser.parse_text(str(resolved)),
            file_url=file_url,
        )

    if suffix in {".docx", ".md", ".txt", ".json", ".csv"}:
        return ArtifactPreviewResponse(
            path=str(resolved),
            file_name=resolved.name,
            kind=suffix.lstrip("."),
            render_mode="text",
            content=parser.parse_text(str(resolved)),
            file_url=file_url,
        )

    return ArtifactPreviewResponse(
        path=str(resolved),
        file_name=resolved.name,
        kind=suffix.lstrip(".") or "file",
        render_mode="download",
        content="",
        file_url=file_url,
    )


@router.get("/file")
def read_artifact_file(
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    resolved = _resolve_artifact_path(path, container)
    _resolve_artifact_access(db, current_user, resolved, container)
    return FileResponse(path=resolved, filename=resolved.name)


@router.get("/download")
def download_artifact_file(
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    resolved = _resolve_artifact_path(path, container)
    _resolve_artifact_access(db, current_user, resolved, container)
    return FileResponse(path=resolved, filename=resolved.name, media_type="application/octet-stream")
