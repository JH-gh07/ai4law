from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.common.trace.tracer import trace_sync
from backend.modules.v0_task_gateway.schema import APIEnvelope, V0TaskCreateRequest
from backend.modules.v0_task_gateway.service import V0TaskGatewayService

router = APIRouter(tags=["v0-task-gateway"])
service = V0TaskGatewayService()


@router.post("/files/upload", response_model=APIEnvelope)
def upload_file(file: UploadFile = File(...)) -> APIEnvelope:
    uploaded = service.upload_file(file)
    return APIEnvelope(data=uploaded)


@router.post("/tasks", response_model=APIEnvelope)
def create_task(payload: V0TaskCreateRequest) -> APIEnvelope:
    try:
        created = trace_sync("v0_task_gateway", lambda: service.create_task(payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"{exc.__class__.__name__}: {exc}") from exc
    return APIEnvelope(data=created)


@router.get("/tasks/{task_id}", response_model=APIEnvelope)
def get_task(task_id: str) -> APIEnvelope:
    try:
        status = service.get_task_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIEnvelope(data=status)


@router.post("/tasks/{task_id}/cancel", response_model=APIEnvelope)
def cancel_task(task_id: str) -> APIEnvelope:
    try:
        status = service.cancel_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIEnvelope(data=status)


@router.get("/tasks/{task_id}/artifacts", response_model=APIEnvelope)
def list_task_artifacts(task_id: str) -> APIEnvelope:
    try:
        artifacts = service.list_task_artifacts(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIEnvelope(data=artifacts)


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    try:
        path = service.resolve_artifact_path(artifact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, filename=path.name)


@router.get("/tasks/{task_id}/audit", response_model=APIEnvelope)
def get_task_audit(task_id: str) -> APIEnvelope:
    try:
        audit = service.get_task_audit(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIEnvelope(data=audit)

