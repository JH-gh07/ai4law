from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import UploadFile

from backend.modules.assessment.schema import AssessmentRequest
from backend.modules.assessment.service import AssessmentService
from backend.modules.dpia.schema import DPIARequest
from backend.modules.dpia.service import DPIAService
from backend.modules.pipia.schema import PIPIARequest
from backend.modules.pipia.service import PIPIAService
from backend.modules.tia.schema import TIARequest
from backend.modules.tia.service import TIAService
from backend.modules.v0_task_gateway.schema import (
    V0ArtifactItem,
    V0TaskArtifactsData,
    V0TaskAuditData,
    V0TaskCreateData,
    V0TaskCreateRequest,
    V0TaskStatusData,
    V0UploadedFileData,
)


@dataclass
class _TaskRef:
    module_code: str


class V0TaskGatewayService:
    """Unified task gateway for v0 API."""

    def __init__(self) -> None:
        self.assessment = AssessmentService()
        self.pipia = PIPIAService()
        self.dpia = DPIAService()
        self.tia = TIAService()
        self._task_refs: dict[str, _TaskRef] = {}
        self._artifact_index: dict[str, Path] = {}
        self._file_index: dict[str, Path] = {}
        self._lock = Lock()
        self.upload_dir = Path("storage/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(self, upload: UploadFile) -> V0UploadedFileData:
        original_name = Path(upload.filename or "uploaded.bin").name
        file_id = f"f_{uuid.uuid4().hex[:16]}"
        safe_name = f"{file_id}_{original_name}"
        out_path = self.upload_dir / safe_name
        payload = upload.file.read()
        out_path.write_bytes(payload)
        with self._lock:
            self._file_index[file_id] = out_path
        return V0UploadedFileData(
            file_id=file_id,
            file_name=original_name,
            mime=upload.content_type or "application/octet-stream",
            size=len(payload),
            path=str(out_path),
            uploaded_at=datetime.now(timezone.utc),
        )

    def create_task(self, req: V0TaskCreateRequest) -> V0TaskCreateData:
        if req.module_code == "2.2":
            payload = self._build_assessment_payload(req.input_payload, req.attachment_ids)
            accepted = self.assessment.submit_async(payload)
        elif req.module_code == "2.3":
            payload = self._build_pipia_payload(req.input_payload, req.attachment_ids)
            accepted = self.pipia.submit_async(payload)
        elif req.module_code == "3.3":
            payload = self._build_dpia_payload(req.input_payload, req.attachment_ids)
            accepted = self.dpia.submit_async(payload)
        elif req.module_code == "3.4":
            payload = self._build_tia_payload(req.input_payload, req.attachment_ids)
            accepted = self.tia.submit_async(payload)
        else:
            raise ValueError(f"Unsupported module_code: {req.module_code}")

        with self._lock:
            self._task_refs[accepted.task_id] = _TaskRef(module_code=req.module_code)
        return V0TaskCreateData(task_id=accepted.task_id, module_code=req.module_code, status=accepted.state)

    def get_task_status(self, task_id: str) -> V0TaskStatusData:
        module_code = self._resolve_module_code(task_id)
        if module_code == "2.2":
            raw = self.assessment.get_async_status(task_id)
        elif module_code == "2.3":
            raw = self.pipia.get_async_status(task_id)
        elif module_code == "3.3":
            raw = self.dpia.get_async_status(task_id)
        elif module_code == "3.4":
            raw = self.tia.get_async_status(task_id)
        else:
            raise KeyError(f"Task not found: {task_id}")

        stage, progress = self._map_stage_progress(raw.state)
        return V0TaskStatusData(
            task_id=raw.task_id,
            module_code=module_code,
            status=raw.state,
            progress=progress,
            stage=stage,
            attempts=raw.attempts,
            max_attempts=raw.max_attempts,
            created_at=raw.created_at,
            updated_at=raw.updated_at,
            error=raw.error,
        )

    def cancel_task(self, task_id: str) -> V0TaskStatusData:
        module_code = self._resolve_module_code(task_id)
        if module_code == "2.2":
            self.assessment.cancel_async(task_id)
        elif module_code == "2.3":
            self.pipia.cancel_async(task_id)
        elif module_code == "3.3":
            self.dpia.cancel_async(task_id)
        elif module_code == "3.4":
            self.tia.cancel_async(task_id)
        else:
            raise KeyError(f"Task not found: {task_id}")
        return self.get_task_status(task_id)

    def list_task_artifacts(self, task_id: str) -> V0TaskArtifactsData:
        module_code = self._resolve_module_code(task_id)
        output_files = self._get_task_output_files(task_id, module_code)
        artifacts: list[V0ArtifactItem] = []
        for file_type, file_path in output_files.items():
            path = Path(file_path)
            if not path.exists():
                continue
            artifact_id = self._make_artifact_id(task_id, file_type, str(path))
            with self._lock:
                self._artifact_index[artifact_id] = path
            artifacts.append(
                V0ArtifactItem(
                    artifact_id=artifact_id,
                    file_name=path.name,
                    file_type=file_type,
                    file_path=str(path),
                    download_url=f"/api/v0/artifacts/{artifact_id}/download",
                )
            )
        return V0TaskArtifactsData(task_id=task_id, module_code=module_code, artifacts=artifacts)

    def resolve_artifact_path(self, artifact_id: str) -> Path:
        with self._lock:
            path = self._artifact_index.get(artifact_id)
        if path is None:
            raise KeyError(f"Artifact not found: {artifact_id}")
        if not path.exists():
            raise KeyError(f"Artifact file missing: {artifact_id}")
        return path

    def get_task_audit(self, task_id: str) -> V0TaskAuditData:
        module_code = self._resolve_module_code(task_id)
        status = self.get_task_status(task_id)
        return V0TaskAuditData(
            task_id=task_id,
            module_code=module_code,
            status=status.status,
            stage=status.stage,
            summary="v0 audit summary: schema/rule/retrieval/generation/render pipeline executed.",
            citations=["法规原文依据", "实务解释依据"],
            model_version="v0-local-llm-adapter",
            template_version="v0",
        )

    def _build_assessment_payload(self, payload: dict[str, Any], attachment_ids: list[str]) -> AssessmentRequest:
        resolved = dict(payload)
        uploaded_files = list(resolved.get("uploaded_files") or [])
        uploaded_files.extend(self._resolve_attachment_paths(attachment_ids))
        resolved["uploaded_files"] = uploaded_files
        return AssessmentRequest.model_validate(resolved)

    def _build_pipia_payload(self, payload: dict[str, Any], attachment_ids: list[str]) -> PIPIARequest:
        resolved = dict(payload)
        attachments = [dict(item) for item in (resolved.get("attachments") or [])]
        for item in attachments:
            item["storage_uri"] = self._resolve_storage_uri(item.get("storage_uri", ""))
            if "file_format" in item and isinstance(item["file_format"], str):
                item["file_format"] = item["file_format"].lower()

        for file_path_str in self._resolve_attachment_paths(attachment_ids):
            file_path = Path(file_path_str)
            suffix = file_path.suffix.lower().lstrip(".") or "docx"
            attachments.append(
                {
                    "file_role": "supporting_evidence",
                    "file_name": file_path.name,
                    "file_format": suffix,
                    "storage_uri": str(file_path),
                }
            )

        resolved["attachments"] = attachments
        return PIPIARequest.model_validate(resolved)

    def _build_dpia_payload(self, payload: dict[str, Any], attachment_ids: list[str]) -> DPIARequest:
        resolved = dict(payload)
        attachments = [dict(item) for item in (resolved.get("attachments") or [])]
        for item in attachments:
            item["storage_uri"] = self._resolve_storage_uri(item.get("storage_uri", ""))
            if "file_format" in item and isinstance(item["file_format"], str):
                item["file_format"] = item["file_format"].lower()

        for file_path_str in self._resolve_attachment_paths(attachment_ids):
            file_path = Path(file_path_str)
            suffix = file_path.suffix.lower().lstrip(".")
            attachments.append(
                {
                    "file_role": "other",
                    "file_name": file_path.name,
                    "file_format": self._normalize_file_format(suffix, {"docx", "pdf", "png", "jpg"}, "pdf"),
                    "storage_uri": str(file_path),
                }
            )
        resolved["attachments"] = attachments
        return DPIARequest.model_validate(resolved)

    def _build_tia_payload(self, payload: dict[str, Any], attachment_ids: list[str]) -> TIARequest:
        resolved = dict(payload)
        attachments = [dict(item) for item in (resolved.get("attachments") or [])]
        for item in attachments:
            item["storage_uri"] = self._resolve_storage_uri(item.get("storage_uri", ""))
            if "file_format" in item and isinstance(item["file_format"], str):
                item["file_format"] = item["file_format"].lower()

        for file_path_str in self._resolve_attachment_paths(attachment_ids):
            file_path = Path(file_path_str)
            suffix = file_path.suffix.lower().lstrip(".")
            attachments.append(
                {
                    "file_role": "other",
                    "file_name": file_path.name,
                    "file_format": self._normalize_file_format(suffix, {"docx", "pdf"}, "pdf"),
                    "storage_uri": str(file_path),
                }
            )
        resolved["attachments"] = attachments
        return TIARequest.model_validate(resolved)

    def _resolve_attachment_paths(self, attachment_ids: list[str]) -> list[str]:
        paths: list[str] = []
        with self._lock:
            index = dict(self._file_index)
        for file_id in attachment_ids:
            file_path = index.get(file_id)
            if file_path is not None:
                paths.append(str(file_path))
                continue
            # Fallback: allow direct filesystem path in v0.
            paths.append(file_id)
        return paths

    def _resolve_storage_uri(self, storage_uri: str) -> str:
        with self._lock:
            index = dict(self._file_index)
        if storage_uri in index:
            return str(index[storage_uri])
        if storage_uri.startswith("storage://uploads/"):
            file_name = storage_uri.replace("storage://uploads/", "", 1)
            for file_path in index.values():
                if file_path.name == file_name:
                    return str(file_path)
            candidate = self.upload_dir / file_name
            return str(candidate)
        return storage_uri

    def _resolve_module_code(self, task_id: str) -> str:
        with self._lock:
            ref = self._task_refs.get(task_id)
        if ref is not None:
            return ref.module_code

        # Fallback lookup in existing module queues.
        for module_code, getter in (
            ("2.2", self.assessment.get_async_status),
            ("2.3", self.pipia.get_async_status),
            ("3.3", self.dpia.get_async_status),
            ("3.4", self.tia.get_async_status),
        ):
            try:
                getter(task_id)
                with self._lock:
                    self._task_refs[task_id] = _TaskRef(module_code=module_code)
                return module_code
            except KeyError:
                continue
        raise KeyError(f"Task not found: {task_id}")

    @staticmethod
    def _map_stage_progress(state: str) -> tuple[str, int]:
        mapping = {
            "CREATED": ("validate_input", 5),
            "RUNNING": ("generate_report", 70),
            "RETRYING": ("retrying", 40),
            "COMPLETED": ("completed", 100),
            "FAILED": ("failed", 100),
            "CANCELED": ("canceled", 100),
        }
        return mapping.get(state, ("unknown", 0))

    def _get_task_output_files(self, task_id: str, module_code: str) -> dict[str, str]:
        if module_code == "2.2":
            status = self.assessment.get_async_status(task_id)
        elif module_code == "2.3":
            status = self.pipia.get_async_status(task_id)
        elif module_code == "3.3":
            status = self.dpia.get_async_status(task_id)
        elif module_code == "3.4":
            status = self.tia.get_async_status(task_id)
        else:
            raise KeyError(f"Task not found: {task_id}")
        if status.result is None:
            return {}
        return dict(status.result.output_files)

    @staticmethod
    def _normalize_file_format(raw: str, allowed: set[str], fallback: str) -> str:
        value = (raw or "").lower().strip()
        if value in allowed:
            return value
        return fallback

    @staticmethod
    def _make_artifact_id(task_id: str, file_type: str, file_path: str) -> str:
        digest = hashlib.sha1(f"{task_id}:{file_type}:{file_path}".encode("utf-8")).hexdigest()[:16]
        return f"art_{digest}"
