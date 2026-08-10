from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models.review import ReviewTaskModel, UploadedFileModel


class ReviewRepository:
    _INTERRUPTED_STATUSES = (
        "PREPARING",
        "SEGMENTING",
        "CLASSIFYING",
        "MISSING_CHECK",
        "REVIEWING",
        "CROSS_DOC_CHECK",
        "AGGREGATING",
        "RENDERING",
    )

    def create_task(self, db: Session, user_id: str) -> ReviewTaskModel:
        record = ReviewTaskModel(user_id=user_id)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_task(self, db: Session, task_id: str, user_id: str) -> ReviewTaskModel | None:
        stmt = select(ReviewTaskModel).where(
            ReviewTaskModel.id == task_id,
            ReviewTaskModel.user_id == user_id,
        )
        return db.execute(stmt).scalar_one_or_none()

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

    def list_files(self, db: Session, task_id: str, user_id: str) -> list[UploadedFileModel]:
        stmt = select(UploadedFileModel).where(
            UploadedFileModel.task_id == task_id,
            UploadedFileModel.user_id == user_id,
        )
        return list(db.scalars(stmt))

    def list_tasks_by_user(self, db: Session, user_id: str, limit: int = 200) -> list[ReviewTaskModel]:
        stmt = (
            select(ReviewTaskModel)
            .where(ReviewTaskModel.user_id == user_id)
            .order_by(ReviewTaskModel.updated_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fail_interrupted_tasks(self, db: Session) -> int:
        result = db.execute(
            update(ReviewTaskModel)
            .where(ReviewTaskModel.status.in_(self._INTERRUPTED_STATUSES))
            .values(status="FAILED")
        )
        db.commit()
        return int(result.rowcount or 0)
