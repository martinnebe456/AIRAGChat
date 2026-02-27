from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    my_role: str | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None
    archive: bool | None = None


class ProjectMemberResponse(BaseModel):
    project_id: str
    user_id: str
    username: str
    email: str
    display_name: str
    role: str
    is_active: bool
    membership_active: bool
    created_at: datetime
    updated_at: datetime


class ProjectMemberListResponse(BaseModel):
    items: list[ProjectMemberResponse]
    total: int


class ProjectMemberCreateRequest(BaseModel):
    user_id: str
    role: str = Field(pattern="^(viewer|contributor|manager)$")
    is_active: bool = True


class ProjectMemberUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(viewer|contributor|manager)$")
    is_active: bool | None = None

