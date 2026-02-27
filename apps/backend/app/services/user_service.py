from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User
from app.db.models.enums import RoleEnum


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(self) -> tuple[list[User], int]:
        items = list(self.db.scalars(select(User).order_by(User.created_at.desc())).all())
        total = self.db.scalar(select(func.count()).select_from(User)) or 0
        return items, int(total)

    def get_user(self, user_id: str) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def create_user(self, *, username: str, email: str, display_name: str, role: str, password: str) -> User:
        if self.db.scalar(select(User).where(User.username == username).limit(1)):
            raise HTTPException(status_code=409, detail="Username already exists")
        if self.db.scalar(select(User).where(User.email == email).limit(1)):
            raise HTTPException(status_code=409, detail="Email already exists")
        user = User(
            username=username,
            email=email,
            display_name=display_name,
            role=RoleEnum(role),
            password_hash=hash_password(password),
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update_user(self, user_id: str, **updates) -> User:  # noqa: ANN003
        user = self.get_user(user_id)
        if "email" in updates and updates["email"] is not None:
            user.email = updates["email"]
        if "display_name" in updates and updates["display_name"] is not None:
            user.display_name = updates["display_name"]
        if "role" in updates and updates["role"] is not None:
            user.role = RoleEnum(str(updates["role"]))
        if "is_active" in updates and updates["is_active"] is not None:
            user.is_active = bool(updates["is_active"])
        self.db.flush()
        return user

    def reset_password(self, user_id: str, *, new_password: str) -> User:
        user = self.get_user(user_id)
        user.password_hash = hash_password(new_password)
        self.db.flush()
        return user

