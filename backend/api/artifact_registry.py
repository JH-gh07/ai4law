from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.core.container import AppContainer
from backend.schemas.auth import AuthUser


def register_module_result_artifacts(
    *,
    db: Session,
    container: AppContainer,
    user: AuthUser,
    module_key: str,
    result,
) -> None:
    paths: dict[str, str] = {}
    report_path = getattr(result, "report_path", None)
    if isinstance(report_path, str) and report_path.strip():
        paths["report"] = report_path

    output_files = getattr(result, "output_files", None)
    if isinstance(output_files, dict):
        for key, value in output_files.items():
            if isinstance(value, str) and value.strip():
                paths[str(key)] = value

    if not paths:
        return

    owner_id = str(uuid4())
    for kind, raw_path in paths.items():
        normalized = str(Path(raw_path).resolve()) if raw_path else raw_path
        artifact_type = (kind or "file").lower()
        container.report_service.register_external_artifact(
            db=db,
            user_id=user.id,
            owner_type=module_key,
            owner_id=owner_id,
            artifact_type=artifact_type,
            file_path=normalized,
            preview={"module": module_key, "kind": artifact_type},
        )
