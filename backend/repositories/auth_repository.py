from datetime import datetime, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from backend.models.auth import AuthSessionModel, UserModel


class AuthRepository:
    def get_user_by_id(self, db: Session, user_id: str) -> UserModel | None:
        return db.get(UserModel, user_id)

    def get_user_by_identifier(self, db: Session, identifier: str) -> UserModel | None:
        normalized = identifier.strip().lower()
        stmt = select(UserModel).where(
            or_(UserModel.username.ilike(normalized), UserModel.email.ilike(normalized))
        )
        return db.execute(stmt).scalar_one_or_none()

    def create_user(self, db: Session, *, username: str, email: str, password_hash: str, company_name: str | None) -> UserModel:
        model = UserModel(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            company_name=(company_name or "").strip(),
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    def create_session(self, db: Session, *, user_id: str, token_hash: str, expires_at: datetime) -> AuthSessionModel:
        model = AuthSessionModel(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    def get_session_by_token_hash(self, db: Session, token_hash: str) -> AuthSessionModel | None:
        stmt = select(AuthSessionModel).where(AuthSessionModel.token_hash == token_hash)
        model = db.execute(stmt).scalar_one_or_none()
        if not model:
            return None
        expires_at = model.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            db.delete(model)
            db.commit()
            return None
        return model

    def delete_session_by_token_hash(self, db: Session, token_hash: str) -> None:
        stmt = delete(AuthSessionModel).where(AuthSessionModel.token_hash == token_hash)
        db.execute(stmt)
        db.commit()
