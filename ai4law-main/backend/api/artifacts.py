from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from backend.common.storage.file_parser import FileParser
from backend.core.dependencies import get_container
from backend.schemas.common import ArtifactPreviewResponse

router = APIRouter()

def _allowed_roots(container) -> list[Path]:
    cwd = Path.cwd().resolve()
    return [
        cwd / "outputs",
        container.settings.storage_dir.resolve(),
        container.settings.report_dir.resolve(),
        container.settings.upload_dir.resolve(),
    ]


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

@router.get("/preview", response_model=ArtifactPreviewResponse)
def preview_artifact(
    path: str = Query(..., min_length=1),
    container=Depends(get_container),
):
    resolved = _resolve_artifact_path(path, container)
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
    container=Depends(get_container),
):
    resolved = _resolve_artifact_path(path, container)
    return FileResponse(path=resolved, filename=resolved.name)
