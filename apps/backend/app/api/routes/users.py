from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.users import (
    AdminResetPasswordRequest,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter()


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("", response_model=UserListResponse)
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> UserListResponse:
    items, total = UserService(db).list_users()
    return UserListResponse(items=[_to_user_response(i) for i in items], total=total)


@router.post("", response_model=UserResponse)
def create_user(
    payload: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> UserResponse:
    service = UserService(db)
    user = service.create_user(
        username=payload.username,
        email=payload.email,
        display_name=payload.display_name,
        role=payload.role,
        password=payload.password,
    )
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="user.create",
        entity_type="user",
        entity_id=user.id,
        after_json={"username": user.username, "role": user.role.value},
        request=request,
    )
    db.commit()
    return _to_user_response(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> UserResponse:
    return _to_user_response(UserService(db).get_user(user_id))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> UserResponse:
    before = UserService(db).get_user(user_id)
    user = UserService(db).update_user(user_id, **payload.model_dump(exclude_unset=True))
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="user.update",
        entity_type="user",
        entity_id=user.id,
        before_json={"email": before.email, "role": before.role.value, "is_active": before.is_active},
        after_json={"email": user.email, "role": user.role.value, "is_active": user.is_active},
        request=request,
    )
    db.commit()
    return _to_user_response(user)


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
def reset_password(
    user_id: str,
    payload: AdminResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> MessageResponse:
    UserService(db).reset_password(user_id, new_password=payload.new_password)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="user.reset_password",
        entity_type="user",
        entity_id=user_id,
        request=request,
    )
    db.commit()
    return MessageResponse(message="Password reset")


@router.post("/{user_id}/activate", response_model=MessageResponse)
def activate_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> MessageResponse:
    UserService(db).update_user(user_id, is_active=True)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="user.activate",
        entity_type="user",
        entity_id=user_id,
        request=request,
    )
    db.commit()
    return MessageResponse(message="User activated")


@router.post("/{user_id}/deactivate", response_model=MessageResponse)
def deactivate_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> MessageResponse:
    UserService(db).update_user(user_id, is_active=False)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="user.deactivate",
        entity_type="user",
        entity_id=user_id,
        request=request,
    )
    db.commit()
    return MessageResponse(message="User deactivated")

