"""
本文件用于定义任务访问控制的服务，包括任务所有权的声明和访问权限的验证。
比如，`claim_task_access` 函数用于声明任务的所有权，`require_task_access` 函数用于验证用户是否有权限访问指定的任务。
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.diagnosis import DiagnosisSessionModel
from backend.models.report import ReportArtifactModel
from backend.models.review import ReviewTaskModel, UploadedFileModel
from backend.models.task import TaskOwnershipModel


def claim_task_access(
    db: Session,
    *,
    task_id: str,
    user_id: str,
    module: str,
) -> TaskOwnershipModel:
    task_id = task_id.strip()
    user_id = user_id.strip()
    module = module.strip()
    if not task_id or not user_id or not module:
        raise ValueError("task_id, user_id and module are required")

    existing = db.get(TaskOwnershipModel, task_id)
    if existing is not None:
        if existing.user_id != user_id or existing.module != module:
            raise ValueError("task ownership conflicts with an existing record")
        return existing

    record = TaskOwnershipModel(task_id=task_id, user_id=user_id, module=module)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _has_legacy_access(db: Session, *, task_id: str, user_id: str) -> bool:
    checks = (
        select(ReportArtifactModel.id).where(
            ReportArtifactModel.owner_id == task_id,
            ReportArtifactModel.user_id == user_id,
        ),
        select(UploadedFileModel.id).where(
            UploadedFileModel.task_id == task_id,
            UploadedFileModel.user_id == user_id,
        ),
        select(ReviewTaskModel.id).where(
            ReviewTaskModel.id == task_id,
            ReviewTaskModel.user_id == user_id,
        ),
        select(DiagnosisSessionModel.id).where(
            DiagnosisSessionModel.id == task_id,
            DiagnosisSessionModel.user_id == user_id,
        ),
    )
    # Legacy tasks may own multiple report artifacts (Markdown, PDF, DOCX, JSON,
    # etc.). Access only needs proof that at least one matching record exists;
    # asking SQLAlchemy for exactly zero-or-one rows raises on valid multi-file
    # reports and turns authorized citation/artifact requests into HTTP 500.
    return any(
        db.execute(statement.limit(1)).scalar_one_or_none() is not None
        for statement in checks
    )


def require_task_access(db: Session, *, task_id: str, user_id: str) -> None:
    owner = db.get(TaskOwnershipModel, task_id)
    if owner is not None and owner.user_id == user_id:
        return
    if owner is None and _has_legacy_access(db, task_id=task_id, user_id=user_id):
        return
    raise HTTPException(status_code=404, detail="Task not found")
