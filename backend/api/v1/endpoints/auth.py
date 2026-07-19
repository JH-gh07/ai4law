from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.schemas.auth import AuthResponse, LoginRequest, MeResponse, RegisterRequest
from backend.services.auth_service import AuthService

router = APIRouter()
service = AuthService()


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    return authorization[len(prefix):].strip()


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return service.register(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return service.login(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> MeResponse:
    token = _extract_bearer_token(authorization)
    user = service.get_user_by_token(db, token or "")
    if not user:
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    return MeResponse(user=user)


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> dict[str, bool]:
    token = _extract_bearer_token(authorization)
    service.logout(db, token or "")
    return {"ok": True}
