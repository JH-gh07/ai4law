from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.common.storage.file_parser import FileParser
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.models.report import ReportArtifactModel
from backend.models.review import UploadedFileModel
from backend.schemas.auth import AuthUser
from backend.schemas.common import ArtifactPreviewResponse

router = APIRouter()


def _artifact_root_aliases(container) -> list[tuple[Path, Path]]:
    """Return each configured artifact root as (logical, physical) paths.

    Release deployments symlink ``storage`` and ``outputs`` into shared runtime
    directories. Database rows retain the logical path while filesystem access
    must use the resolved physical path, so authorization needs both identities.
    """
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


def _assert_artifact_access(db: Session, user: AuthUser, resolved: Path, container) -> None:
    candidate_paths = tuple(_candidate_artifact_paths(resolved, container))
    report_stmt = select(ReportArtifactModel.id).where(
        ReportArtifactModel.user_id == user.id,
        ReportArtifactModel.file_path.in_(candidate_paths),
    )
    upload_stmt = select(UploadedFileModel.id).where(
        UploadedFileModel.user_id == user.id,
        UploadedFileModel.storage_path.in_(candidate_paths),
    )
    report_hit = db.execute(report_stmt).scalar_one_or_none()
    upload_hit = db.execute(upload_stmt).scalar_one_or_none()
    if report_hit or upload_hit:
        return
    raise HTTPException(status_code=403, detail="You do not have access to this artifact.")

@router.get("/preview", response_model=ArtifactPreviewResponse)
def preview_artifact(
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    resolved = _resolve_artifact_path(path, container)
    _assert_artifact_access(db, current_user, resolved, container)
    suffix = resolved.suffix.lower()
    parser = FileParser()
    file_url = f"/api/v1/artifacts/file?path={quote(str(resolved))}"

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
    _assert_artifact_access(db, current_user, resolved, container)
    return FileResponse(path=resolved, filename=resolved.name)


@router.get("/download")
def download_artifact_file(
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
):
    resolved = _resolve_artifact_path(path, container)
    _assert_artifact_access(db, current_user, resolved, container)
    return FileResponse(path=resolved, filename=resolved.name, media_type="application/octet-stream")
