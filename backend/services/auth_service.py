from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.repositories.auth_repository import AuthRepository
from backend.schemas.auth import AuthResponse, AuthUser, LoginRequest, RegisterRequest


class AuthService:
    def __init__(self) -> None:
        self.repository = AuthRepository()

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _assert_email_like(email: str) -> None:
        cleaned = email.strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("邮箱格式不正确")

    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> str:
        salt_bytes = (salt or secrets.token_hex(16)).encode("utf-8")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 120_000)
        return f"pbkdf2_sha256${salt_bytes.decode('utf-8')}${digest.hex()}"

    @staticmethod
    def _verify_password(password: str, encoded: str) -> bool:
        try:
            algorithm, salt, digest = encoded.split("$", 2)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        expected = AuthService._hash_password(password, salt)
        return hmac.compare_digest(expected, encoded)

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _to_user_schema(model) -> AuthUser:
        return AuthUser(
            id=model.id,
            username=model.username,
            email=model.email,
            company_name=model.company_name or None,
        )

    def register(self, db: Session, payload: RegisterRequest) -> AuthResponse:
        self._assert_email_like(payload.email)
        if self.repository.get_user_by_identifier(db, payload.username):
            raise ValueError("用户名已存在")
        if self.repository.get_user_by_identifier(db, self._normalize_email(payload.email)):
            raise ValueError("邮箱已被注册")

        user = self.repository.create_user(
            db,
            username=payload.username,
            email=self._normalize_email(payload.email),
            password_hash=self._hash_password(payload.password),
            company_name=payload.company_name,
        )
        raw_token = secrets.token_urlsafe(40)
        token_hash = self._hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=14)
        self.repository.create_session(db, user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        return AuthResponse(access_token=raw_token, user=self._to_user_schema(user))

    def login(self, db: Session, payload: LoginRequest) -> AuthResponse:
        identifier = payload.identifier.strip()
        user = self.repository.get_user_by_identifier(db, identifier)
        if not user or not self._verify_password(payload.password, user.password_hash):
            raise ValueError("用户名/邮箱或密码错误")

        raw_token = secrets.token_urlsafe(40)
        token_hash = self._hash_token(raw_token)
        ttl_days = 14 if payload.remember else 1
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        self.repository.create_session(db, user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        return AuthResponse(access_token=raw_token, user=self._to_user_schema(user))

    def get_user_by_token(self, db: Session, token: str) -> AuthUser | None:
        if not token:
            return None
        token_hash = self._hash_token(token)
        session = self.repository.get_session_by_token_hash(db, token_hash)
        if not session:
            return None
        user = self.repository.get_user_by_id(db, session.user_id)
        if not user:
            self.repository.delete_session_by_token_hash(db, token_hash)
            return None
        return self._to_user_schema(user)

    def logout(self, db: Session, token: str) -> None:
        if not token:
            return
        token_hash = self._hash_token(token)
        self.repository.delete_session_by_token_hash(db, token_hash)
