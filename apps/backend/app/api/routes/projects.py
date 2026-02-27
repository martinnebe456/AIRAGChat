from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.models import Project, ProjectMembership, User
from app.db.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberCreateRequest,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectMemberUpdateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.audit_service import AuditService
from app.services.project_service import ProjectService

router = APIRouter()


def _project_response(project: Project, membership: ProjectMembership | None = None) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        is_active=project.is_active,
        archived_at=project.archived_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        my_role=(membership.role.value if membership and hasattr(membership.role, "value") else (str(membership.role) if membership else None)),
    )


def _member_response(project_id: str, membership: ProjectMembership, user: User) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        project_id=project_id,
        user_id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        role=membership.role.value if hasattr(membership.role, "value") else str(membership.role),
        is_active=user.is_active,
        membership_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    rows, total = ProjectService(db).list_projects_for_user(user=current_user)
    return ProjectListResponse(items=[_project_response(p, m) for p, m in rows], total=total)


@router.post("", response_model=ProjectResponse)
def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    service = ProjectService(db)
    project = service.create_project(
        actor=current_user,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="project.create",
        entity_type="project",
        entity_id=project.id,
        request=request,
        after_json={"name": project.name, "slug": project.slug},
    )
    db.commit()
    _p, membership = service.get_project_for_user(project_id=project.id, user=current_user)
    return _project_response(project, membership)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    project, membership = ProjectService(db).get_project_for_user(project_id=project_id, user=current_user)
    return _project_response(project, membership)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    service = ProjectService(db)
    project = service.update_project(project_id=project_id, actor=current_user, **payload.model_dump(exclude_unset=True))
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="project.update",
        entity_type="project",
        entity_id=project.id,
        request=request,
    )
    db.commit()
    project, membership = service.get_project_for_user(project_id=project.id, user=current_user)
    return _project_response(project, membership)


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    project = ProjectService(db).delete_project(project_id=project_id, actor=current_user)
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="project.delete",
        entity_type="project",
        entity_id=project.id,
        request=request,
    )
    db.commit()
    return MessageResponse(message="Project deleted")


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
def list_project_members(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectMemberListResponse:
    rows, total = ProjectService(db).list_members(project_id=project_id, actor=current_user)
    return ProjectMemberListResponse(items=[_member_response(project_id, m, u) for m, u in rows], total=total)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
def add_project_member(
    project_id: str,
    payload: ProjectMemberCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectMemberResponse:
    service = ProjectService(db)
    membership = service.add_member(
        project_id=project_id,
        actor=current_user,
        user_id=payload.user_id,
        role=payload.role,
        is_active=payload.is_active,
    )
    user = db.get(User, payload.user_id)
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="project.member.add",
        entity_type="project_membership",
        entity_id=membership.id,
        request=request,
        after_json={"project_id": project_id, "user_id": payload.user_id, "role": payload.role},
    )
    db.commit()
    return _member_response(project_id, membership, user)  # type: ignore[arg-type]


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_project_member(
    project_id: str,
    user_id: str,
    payload: ProjectMemberUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectMemberResponse:
    service = ProjectService(db)
    membership = service.update_member(
        project_id=project_id,
        target_user_id=user_id,
        actor=current_user,
        role=payload.role,
        is_active=payload.is_active,
    )
    user = db.get(User, user_id)
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="project.member.update",
        entity_type="project_membership",
        entity_id=membership.id,
        request=request,
        after_json={"project_id": project_id, "user_id": user_id, "role": payload.role, "is_active": payload.is_active},
    )
    db.commit()
    return _member_response(project_id, membership, user)  # type: ignore[arg-type]


@router.delete("/{project_id}/members/{user_id}", response_model=MessageResponse)
def delete_project_member(
    project_id: str,
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    membership = ProjectService(db).remove_member(project_id=project_id, target_user_id=user_id, actor=current_user)
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="project.member.delete",
        entity_type="project_membership",
        entity_id=membership.id,
        request=request,
        after_json={"project_id": project_id, "user_id": user_id},
    )
    db.commit()
    return MessageResponse(message="Project member removed")

