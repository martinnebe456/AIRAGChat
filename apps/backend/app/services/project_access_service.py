from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models import Project, ProjectMembership, User
from app.db.models.enums import ProjectMembershipRoleEnum, RoleEnum


_ROLE_ORDER = {
    ProjectMembershipRoleEnum.VIEWER.value: 1,
    ProjectMembershipRoleEnum.CONTRIBUTOR.value: 2,
    ProjectMembershipRoleEnum.MANAGER.value: 3,
}


class ProjectAccessService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def is_admin(user: User) -> bool:
        return user.role == RoleEnum.ADMIN

    def get_project(self, project_id: str, *, allow_inactive: bool = False) -> Project:
        project = self.db.get(Project, project_id)
        if not project or project.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if not allow_inactive and (not project.is_active or project.archived_at is not None):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    def get_membership(self, *, project_id: str, user_id: str) -> ProjectMembership | None:
        return self.db.scalar(
            select(ProjectMembership)
            .where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            )
            .limit(1)
        )

    def require_project_role(
        self,
        *,
        project_id: str,
        user: User,
        minimum_role: str = "viewer",
        allow_inactive_project: bool = False,
    ) -> tuple[Project, ProjectMembership | None]:
        project = self.get_project(project_id, allow_inactive=allow_inactive_project)
        if self.is_admin(user):
            return project, None
        membership = self.get_membership(project_id=project_id, user_id=user.id)
        if membership is None or not membership.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to project")
        current_rank = _ROLE_ORDER.get(membership.role.value if hasattr(membership.role, "value") else str(membership.role), 0)
        required_rank = _ROLE_ORDER.get(str(minimum_role), 1)
        if current_rank < required_rank:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient project permissions")
        return project, membership

    def list_accessible_projects(self, *, user: User, include_inactive: bool = False) -> list[tuple[Project, ProjectMembership | None]]:
        if self.is_admin(user):
            stmt = select(Project).where(Project.deleted_at.is_(None))
            if not include_inactive:
                stmt = stmt.where(Project.is_active.is_(True), Project.archived_at.is_(None))
            rows = list(self.db.scalars(stmt.order_by(Project.name.asc())).all())
            return [(p, None) for p in rows]

        stmt = (
            select(Project, ProjectMembership)
            .join(ProjectMembership, and_(ProjectMembership.project_id == Project.id, ProjectMembership.user_id == user.id))
            .where(Project.deleted_at.is_(None), ProjectMembership.is_active.is_(True))
        )
        if not include_inactive:
            stmt = stmt.where(Project.is_active.is_(True), Project.archived_at.is_(None))
        result = self.db.execute(stmt.order_by(Project.name.asc())).all()
        return [(row[0], row[1]) for row in result]

    def list_accessible_project_ids(self, *, user: User, minimum_role: str = "viewer") -> set[str]:
        if self.is_admin(user):
            rows = self.db.scalars(select(Project.id).where(Project.deleted_at.is_(None))).all()
            return set(rows)
        required_rank = _ROLE_ORDER.get(str(minimum_role), 1)
        memberships = list(
            self.db.scalars(
                select(ProjectMembership)
                .where(ProjectMembership.user_id == user.id, ProjectMembership.is_active.is_(True))
            ).all()
        )
        allowed: set[str] = set()
        for m in memberships:
            rank = _ROLE_ORDER.get(m.role.value if hasattr(m.role, "value") else str(m.role), 0)
            if rank >= required_rank:
                allowed.add(m.project_id)
        return allowed

