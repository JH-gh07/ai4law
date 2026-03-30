from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.report import ReportArtifactModel


class ReportRepository:
    def create(self, db: Session, report: ReportArtifactModel) -> ReportArtifactModel:
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def list_for_owner(self, db: Session, owner_type: str, owner_id: str) -> list[ReportArtifactModel]:
        stmt = select(ReportArtifactModel).where(
            ReportArtifactModel.owner_type == owner_type,
            ReportArtifactModel.owner_id == owner_id,
        )
        return list(db.scalars(stmt))

    def get_by_owner_and_type(self, db: Session, owner_type: str, owner_id: str, artifact_type: str) -> ReportArtifactModel | None:
        stmt = select(ReportArtifactModel).where(
            ReportArtifactModel.owner_type == owner_type,
            ReportArtifactModel.owner_id == owner_id,
            ReportArtifactModel.artifact_type == artifact_type,
        )
        return db.scalars(stmt).first()
