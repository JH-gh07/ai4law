from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.diagnosis import DiagnosisSessionModel


class DiagnosisRepository:
    def create(self, db: Session, user_id: str) -> DiagnosisSessionModel:
        record = DiagnosisSessionModel(user_id=user_id)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get(self, db: Session, session_id: str, user_id: str) -> DiagnosisSessionModel | None:
        stmt = select(DiagnosisSessionModel).where(
            DiagnosisSessionModel.id == session_id,
            DiagnosisSessionModel.user_id == user_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    def save(self, db: Session, record: DiagnosisSessionModel) -> DiagnosisSessionModel:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def list_by_user(self, db: Session, user_id: str, limit: int = 200) -> list[DiagnosisSessionModel]:
        stmt = (
            select(DiagnosisSessionModel)
            .where(DiagnosisSessionModel.user_id == user_id)
            .order_by(DiagnosisSessionModel.updated_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))
