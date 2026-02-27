from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class UserMeResponse(BaseModel):
    id: str
    username: str
    # Keep local-dev addresses such as `*.local` valid in API responses.
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
