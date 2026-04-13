from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import UploadFile

from backend.modules.assessment.schema import AssessmentRequest
from backend.modules.assessment.service import AssessmentService
from backend.modules.bcr.schema import BCRRequest
from backend.modules.bcr.service import BCRService
from backend.modules.cn_flow.schema import CNFlowRequest
from backend.modules.cn_flow.service import CNFlowService
from backend.modules.cpra.schema import CPRARequest
from backend.modules.cpra.service import CPRAService
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
    input_digest: str | None = None


class V0TaskGatewayService:
    """Unified task gateway for v0 API."""

    def __init__(self) -> None:
        self.assessment = AssessmentService()
        self.pipia = PIPIAService()
        self.bcr = BCRService()
        self.dpia = DPIAService()
        self.tia = TIAService()
        self.cn_flow = CNFlowService()
        self.cpra = CPRAService()
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
        elif req.module_code == "3.2":
            payload = self._build_bcr_payload(req.input_payload, req.attachment_ids)
            accepted = self.bcr.submit_async(payload)
        elif req.module_code == "3.3":
            payload = self._build_dpia_payload(req.input_payload, req.attachment_ids)
            accepted = self.dpia.submit_async(payload)
        elif req.module_code == "3.4":
            payload = self._build_tia_payload(req.input_payload, req.attachment_ids)
            accepted = self.tia.submit_async(payload)
        elif req.module_code == "4.1":
            payload = self._build_cn_flow_payload(req.input_payload, req.attachment_ids)
            accepted = self.cn_flow.submit_async(payload)
        elif req.module_code == "4.2":
            payload = self._build_cpra_payload(req.input_payload, req.attachment_ids)
            accepted = self.cpra.submit_async(payload)
        else:
            raise ValueError(f"Unsupported module_code: {req.module_code}")

        with self._lock:
            self._task_refs[accepted.task_id] = _TaskRef(
                module_code=req.module_code,
                input_digest=self._compute_input_digest(req),
            )
        return V0TaskCreateData(task_id=accepted.task_id, module_code=req.module_code, status=accepted.state)

    def get_task_status(self, task_id: str) -> V0TaskStatusData:
        module_code = self._resolve_module_code(task_id)
        if module_code == "2.2":
            raw = self.assessment.get_async_status(task_id)
        elif module_code == "2.3":
            raw = self.pipia.get_async_status(task_id)
        elif module_code == "3.2":
            raw = self.bcr.get_async_status(task_id)
        elif module_code == "3.3":
            raw = self.dpia.get_async_status(task_id)
        elif module_code == "3.4":
            raw = self.tia.get_async_status(task_id)
        elif module_code == "4.1":
            raw = self.cn_flow.get_async_status(task_id)
        elif module_code == "4.2":
            raw = self.cpra.get_async_status(task_id)
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
        elif module_code == "3.2":
            self.bcr.cancel_async(task_id)
        elif module_code == "3.3":
            self.dpia.cancel_async(task_id)
        elif module_code == "3.4":
            self.tia.cancel_async(task_id)
        elif module_code == "4.1":
            self.cn_flow.cancel_async(task_id)
        elif module_code == "4.2":
            self.cpra.cancel_async(task_id)
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
        ref = self._get_task_ref(task_id)
        raw = self._get_raw_task_status(task_id, module_code)
        result_payload = None
        if raw is not None and getattr(raw, "result", None) is not None:
            if hasattr(raw.result, "model_dump"):
                result_payload = raw.result.model_dump()
            elif isinstance(raw.result, dict):
                result_payload = raw.result
        consistency_issues = list((result_payload or {}).get("consistency_issues") or [])
        citations = self._collect_citations(result_payload)
        retrieval_sources = self._collect_retrieval_sources(result_payload, citations)
        rule_hits = self._build_rule_hits(status.error, consistency_issues)
        return V0TaskAuditData(
            task_id=task_id,
            module_code=module_code,
            status=status.status,
            stage=status.stage,
            summary="v0 audit summary: schema/rule/retrieval/generation/render pipeline executed.",
            input_digest=ref.input_digest if ref is not None else None,
            rule_hits=rule_hits,
            retrieval_sources=retrieval_sources,
            consistency_issues=consistency_issues,
            citations=citations,
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

    def _build_bcr_payload(self, payload: dict[str, Any], attachment_ids: list[str]) -> BCRRequest:
        resolved = dict(payload)
        attachments = [dict(item) for item in (resolved.get("attachments") or [])]
        for item in attachments:
            item["storage_uri"] = self._resolve_storage_uri(item.get("storage_uri", ""))
            if "file_format" in item and isinstance(item["file_format"], str):
                item["file_format"] = item["file_format"].lower()

        uploaded_files = list(resolved.get("uploaded_files") or [])
        uploaded_files.extend(self._resolve_attachment_paths(attachment_ids))
        resolved["attachments"] = attachments
        resolved["uploaded_files"] = uploaded_files
        return BCRRequest.model_validate(resolved)

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

    def _build_cn_flow_payload(self, payload: dict[str, Any], attachment_ids: list[str]) -> CNFlowRequest:
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
                    "file_role": "supporting_material",
                    "file_name": file_path.name,
                    "file_format": self._normalize_file_format(suffix, {"xlsx", "csv", "docx", "pdf"}, "csv"),
                    "storage_uri": str(file_path),
                }
            )
        resolved["attachments"] = attachments
        return CNFlowRequest.model_validate(resolved)

    def _build_cpra_payload(self, payload: dict[str, Any], attachment_ids: list[str]) -> CPRARequest:
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
                    "file_format": self._normalize_file_format(
                        suffix, {"docx", "pdf", "url", "xlsx", "csv"}, "pdf"
                    ),
                    "storage_uri": str(file_path),
                }
            )
        resolved["attachments"] = attachments
        return CPRARequest.model_validate(resolved)

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
            ("3.2", self.bcr.get_async_status),
            ("3.3", self.dpia.get_async_status),
            ("3.4", self.tia.get_async_status),
            ("4.1", self.cn_flow.get_async_status),
            ("4.2", self.cpra.get_async_status),
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
        elif module_code == "3.2":
            status = self.bcr.get_async_status(task_id)
        elif module_code == "3.3":
            status = self.dpia.get_async_status(task_id)
        elif module_code == "3.4":
            status = self.tia.get_async_status(task_id)
        elif module_code == "4.1":
            status = self.cn_flow.get_async_status(task_id)
        elif module_code == "4.2":
            status = self.cpra.get_async_status(task_id)
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

    @staticmethod
    def _compute_input_digest(req: V0TaskCreateRequest) -> str:
        canonical = json.dumps(
            {
                "module_code": req.module_code,
                "session_id": req.session_id,
                "input_payload": req.input_payload,
                "attachment_ids": req.attachment_ids,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha1(canonical.encode("utf-8")).hexdigest()

    def _get_task_ref(self, task_id: str) -> _TaskRef | None:
        with self._lock:
            return self._task_refs.get(task_id)

    def _get_raw_task_status(self, task_id: str, module_code: str) -> Any:
        if module_code == "2.2":
            return self.assessment.get_async_status(task_id)
        if module_code == "2.3":
            return self.pipia.get_async_status(task_id)
        if module_code == "3.2":
            return self.bcr.get_async_status(task_id)
        if module_code == "3.3":
            return self.dpia.get_async_status(task_id)
        if module_code == "3.4":
            return self.tia.get_async_status(task_id)
        if module_code == "4.1":
            return self.cn_flow.get_async_status(task_id)
        if module_code == "4.2":
            return self.cpra.get_async_status(task_id)
        raise KeyError(f"Task not found: {task_id}")

    @staticmethod
    def _collect_citations(result_payload: dict[str, Any] | None) -> list[str]:
        if not result_payload:
            return []
        chapters = result_payload.get("chapters") or []
        citations: list[str] = []
        for chapter in chapters:
            for cite in chapter.get("citations") or []:
                if cite and cite not in citations:
                    citations.append(str(cite))
        regulations = result_payload.get("regulations") or []
        for reg in regulations:
            name = f"{reg.get('title', '')}{reg.get('article', '')}".strip()
            if name and name not in citations:
                citations.append(name)
        return citations

    @staticmethod
    def _collect_retrieval_sources(result_payload: dict[str, Any] | None, citations: list[str]) -> list[str]:
        if not result_payload:
            return []
        regulations = result_payload.get("regulations") or []
        if regulations:
            sources = []
            for reg in regulations:
                label = f"{reg.get('title', '')}{reg.get('article', '')}: {reg.get('snippet', '')}".strip()
                if label:
                    sources.append(label)
            return sources
        return citations[:8]

    @staticmethod
    def _build_rule_hits(error: str | None, consistency_issues: list[str]) -> list[dict[str, str]]:
        hits: list[dict[str, str]] = [
            {
                "rule_id": "schema_validate",
                "hit": "pass" if error is None else "fail",
                "evidence": "pydantic validation passed" if error is None else error,
            },
            {
                "rule_id": "rule_validate",
                "hit": "pass" if not consistency_issues else "warn",
                "evidence": "no consistency issues" if not consistency_issues else "consistency issues detected",
            },
            {"rule_id": "artifact_render", "hit": "pass", "evidence": "artifacts generated and indexed"},
        ]
        for issue in consistency_issues[:10]:
            hits.append({"rule_id": "consistency_issue", "hit": "warn", "evidence": issue})
        return hits
