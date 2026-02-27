from __future__ import annotations

from enum import Enum


class RoleEnum(str, Enum):
    USER = "user"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"


class ProjectMembershipRoleEnum(str, Enum):
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    MANAGER = "manager"


class DocumentStatusEnum(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ProviderModeEnum(str, Enum):
    OPENAI_API = "openai_api"

