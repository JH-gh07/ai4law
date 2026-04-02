from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.review import ReviewTaskModel, UploadedFileModel


class ReviewRepository:
    def create_task(self, db: Session, **fields) -> ReviewTaskModel:
        record = ReviewTaskModel(**fields)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_task(self, db: Session, task_id: str) -> ReviewTaskModel | None:
        return db.get(ReviewTaskModel, task_id)

    def save_task(self, db: Session, record: ReviewTaskModel) -> ReviewTaskModel:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def create_file(self, db: Session, uploaded_file: UploadedFileModel) -> UploadedFileModel:
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)
        return uploaded_file

    def list_files(self, db: Session, task_id: str) -> list[UploadedFileModel]:
        stmt = select(UploadedFileModel).where(UploadedFileModel.task_id == task_id)
        return list(db.scalars(stmt))
