from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.container import AppContainer
from backend.schemas.auth import AuthUser
from backend.services.auth_service import AuthService

auth_service = AuthService()


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_db(container: AppContainer = Depends(get_container)) -> Generator[Session, None, None]:
    db = container.session_factory()
    try:
        yield db
    finally:
        db.close()


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return ""
    return authorization[len(prefix):].strip()


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> AuthUser:
    token = _extract_bearer_token(authorization)
    user = auth_service.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    return user
