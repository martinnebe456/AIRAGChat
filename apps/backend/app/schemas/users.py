from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _normalize_and_validate_email(value: str) -> str:
    email = value.strip()
    if not email or "@" not in email:
        raise ValueError("Invalid email address")
    local_part, _, domain_part = email.partition("@")
    if not local_part or not domain_part or "." not in domain_part:
        raise ValueError("Invalid email address")
    if len(email) > 254:
        raise ValueError("Email address is too long")
    return email


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str
    display_name: str = Field(min_length=1, max_length=255)
    role: str = Field(pattern="^(user|contributor|admin)$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_and_validate_email(value)


class UserUpdateRequest(BaseModel):
    email: str | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, pattern="^(user|contributor|admin)$")
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_and_validate_email(value)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
