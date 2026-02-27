from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.jwt import create_access_token
from app.core.security import generate_opaque_token, hash_opaque_token, verify_password
from app.db.models import RefreshToken, User


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def authenticate(self, *, username_or_email: str, password: str) -> tuple[User, str, RefreshToken, str]:
        user = self.db.scalar(
            select(User).where(
                or_(User.username == username_or_email, User.email == username_or_email)
            ).limit(1)
        )
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        user.last_login_at = datetime.now(UTC)
        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token_plain = generate_opaque_token()
        refresh_row = RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(refresh_token_plain),
            jti=secrets.token_hex(16),
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days),
        )
        self.db.add(refresh_row)
        self.db.flush()
        return user, access_token, refresh_row, refresh_token_plain

    def refresh(self, *, refresh_token_plain: str) -> tuple[User, str, RefreshToken, str]:
        row = self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(refresh_token_plain)).limit(1)
        )
        if not row or row.revoked_at or row.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user = self.db.get(User, row.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        row.revoked_at = datetime.now(UTC)
        new_plain = generate_opaque_token()
        new_row = RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(new_plain),
            jti=secrets.token_hex(16),
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days),
            rotated_from_token_id=row.id,
        )
        self.db.add(new_row)
        access_token = create_access_token(subject=user.id, role=user.role.value)
        self.db.flush()
        return user, access_token, new_row, new_plain

    def logout(self, *, refresh_token_plain: str | None) -> None:
        if not refresh_token_plain:
            return
        row = self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(refresh_token_plain)).limit(1)
        )
        if row and not row.revoked_at:
            row.revoked_at = datetime.now(UTC)
            self.db.flush()

