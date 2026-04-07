from sqlalchemy.orm import Session

from backend.models.diagnosis import DiagnosisSessionModel


class DiagnosisRepository:
    def create(self, db: Session) -> DiagnosisSessionModel:
        record = DiagnosisSessionModel()
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get(self, db: Session, session_id: str) -> DiagnosisSessionModel | None:
        return db.get(DiagnosisSessionModel, session_id)

    def save(self, db: Session, record: DiagnosisSessionModel) -> DiagnosisSessionModel:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
