from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.report import ReportArtifactModel


class ReportRepository:
    def create(self, db: Session, report: ReportArtifactModel) -> ReportArtifactModel:
        db.add(report)
        db.commit()
        db.refresh(report)
        return report


    def get_by_owner_and_type(self, db: Session, user_id: str, owner_type: str, owner_id: str, artifact_type: str) -> ReportArtifactModel | None:
        stmt = select(ReportArtifactModel).where(
            ReportArtifactModel.user_id == user_id,
            ReportArtifactModel.owner_type == owner_type,
            ReportArtifactModel.owner_id == owner_id,
            ReportArtifactModel.artifact_type == artifact_type,
        )
        return db.scalars(stmt).first()


    def get_by_user_and_path(self, db: Session, user_id: str, file_path: str) -> ReportArtifactModel | None:
        stmt = select(ReportArtifactModel).where(
            ReportArtifactModel.user_id == user_id,
            ReportArtifactModel.file_path == file_path,
        )
        return db.scalars(stmt).first()

    def list_by_user(self, db: Session, user_id: str, limit: int = 400) -> list[ReportArtifactModel]:
        stmt = (
            select(ReportArtifactModel)
            .where(ReportArtifactModel.user_id == user_id)
            .order_by(ReportArtifactModel.created_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def list_by_user_and_owner(self, db: Session, user_id: str, owner_id: str) -> list[ReportArtifactModel]:
        stmt = (
            select(ReportArtifactModel)
            .where(
                ReportArtifactModel.user_id == user_id,
                ReportArtifactModel.owner_id == owner_id,
            )
            .order_by(ReportArtifactModel.created_at.desc())
        )
        return list(db.scalars(stmt))
