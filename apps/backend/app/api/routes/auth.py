from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import enforce_rate_limit
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter()


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=max_age,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    enforce_rate_limit("login", request.client.host if request.client else "unknown")
    service = AuthService(db)
    user, access_token, _refresh_row, refresh_plain = service.authenticate(
        username_or_email=payload.username_or_email,
        password=payload.password,
    )
    _set_refresh_cookie(response, refresh_plain)
    db.commit()
    settings = get_settings()
    return TokenResponse(access_token=access_token, expires_in_seconds=settings.access_token_expire_minutes * 60)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    refresh_cookie = request.cookies.get("refresh_token")
    service = AuthService(db)
    _user, access_token, _row, new_refresh_plain = service.refresh(refresh_token_plain=refresh_cookie or "")
    _set_refresh_cookie(response, new_refresh_plain)
    db.commit()
    settings = get_settings()
    return TokenResponse(access_token=access_token, expires_in_seconds=settings.access_token_expire_minutes * 60)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> MessageResponse:
    service = AuthService(db)
    service.logout(refresh_token_plain=request.cookies.get("refresh_token"))
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    db.commit()
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserMeResponse)
def me(current_user: User = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        last_login_at=current_user.last_login_at,
    )

