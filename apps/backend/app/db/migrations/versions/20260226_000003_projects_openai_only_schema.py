"""projects and project-scoped chat/documents schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260226_000003"
down_revision = "20260225_000002"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in _inspector().get_indexes(table_name))


def _fk_exists(table_name: str, constrained_columns: list[str], referred_table: str) -> bool:
    wanted = set(constrained_columns)
    for fk in _inspector().get_foreign_keys(table_name):
        if fk.get("referred_table") != referred_table:
            continue
        if set(fk.get("constrained_columns") or []) == wanted:
            return True
    return False


def upgrade() -> None:
    project_role_enum = postgresql.ENUM("viewer", "contributor", "manager", name="projectmembershiproleenum", create_type=False)
    project_role_enum.create(op.get_bind(), checkfirst=True)

    if not _has_table("projects"):
        op.create_table(
            "projects",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _has_table("projects"):
        if not _has_index("projects", op.f("ix_projects_slug")):
            op.create_index(op.f("ix_projects_slug"), "projects", ["slug"], unique=True)
        if not _has_index("projects", op.f("ix_projects_is_active")):
            op.create_index(op.f("ix_projects_is_active"), "projects", ["is_active"], unique=False)
        if not _has_index("projects", op.f("ix_projects_created_by_user_id")):
            op.create_index(op.f("ix_projects_created_by_user_id"), "projects", ["created_by_user_id"], unique=False)

    if not _has_table("project_memberships"):
        op.create_table(
            "project_memberships",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("role", project_role_enum, nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("project_id", "user_id", name="uq_project_memberships_project_user"),
        )
    if _has_table("project_memberships"):
        if not _has_index("project_memberships", op.f("ix_project_memberships_project_id")):
            op.create_index(op.f("ix_project_memberships_project_id"), "project_memberships", ["project_id"], unique=False)
        if not _has_index("project_memberships", op.f("ix_project_memberships_user_id")):
            op.create_index(op.f("ix_project_memberships_user_id"), "project_memberships", ["user_id"], unique=False)
        if not _has_index("project_memberships", op.f("ix_project_memberships_is_active")):
            op.create_index(op.f("ix_project_memberships_is_active"), "project_memberships", ["is_active"], unique=False)
        if not _has_index("project_memberships", op.f("ix_project_memberships_created_by_user_id")):
            op.create_index(
                op.f("ix_project_memberships_created_by_user_id"),
                "project_memberships",
                ["created_by_user_id"],
                unique=False,
            )

    if not _has_column("documents", "project_id"):
        op.add_column("documents", sa.Column("project_id", sa.String(length=36), nullable=True))
    if not _has_column("documents", "page_count"):
        op.add_column("documents", sa.Column("page_count", sa.Integer(), nullable=True))
    if not _has_column("documents", "parser_metadata_json"):
        op.add_column("documents", sa.Column("parser_metadata_json", sa.JSON(), nullable=True))
    if not _has_column("documents", "processing_progress_json"):
        op.add_column("documents", sa.Column("processing_progress_json", sa.JSON(), nullable=True))
    if _has_column("documents", "project_id") and not _has_index("documents", op.f("ix_documents_project_id")):
        op.create_index(op.f("ix_documents_project_id"), "documents", ["project_id"], unique=False)
    if _has_column("documents", "project_id") and not _fk_exists("documents", ["project_id"], "projects"):
        op.create_foreign_key(None, "documents", "projects", ["project_id"], ["id"], ondelete="CASCADE")

    if not _has_column("document_processing_jobs", "project_id"):
        op.add_column("document_processing_jobs", sa.Column("project_id", sa.String(length=36), nullable=True))
    if not _has_column("document_processing_jobs", "progress_json"):
        op.add_column("document_processing_jobs", sa.Column("progress_json", sa.JSON(), nullable=True))
    if not _has_column("document_processing_jobs", "cancellation_requested"):
        op.add_column(
            "document_processing_jobs",
            sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if _has_column("document_processing_jobs", "project_id") and not _has_index(
        "document_processing_jobs", op.f("ix_document_processing_jobs_project_id")
    ):
        op.create_index(op.f("ix_document_processing_jobs_project_id"), "document_processing_jobs", ["project_id"], unique=False)
    if _has_column("document_processing_jobs", "project_id") and not _fk_exists(
        "document_processing_jobs", ["project_id"], "projects"
    ):
        op.create_foreign_key(
            None,
            "document_processing_jobs",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _has_column("chat_sessions", "project_id"):
        op.add_column("chat_sessions", sa.Column("project_id", sa.String(length=36), nullable=True))
    if _has_column("chat_sessions", "project_id") and not _has_index("chat_sessions", op.f("ix_chat_sessions_project_id")):
        op.create_index(op.f("ix_chat_sessions_project_id"), "chat_sessions", ["project_id"], unique=False)
    if _has_column("chat_sessions", "project_id") and not _fk_exists("chat_sessions", ["project_id"], "projects"):
        op.create_foreign_key(None, "chat_sessions", "projects", ["project_id"], ["id"], ondelete="CASCADE")

    if not _has_column("chat_messages", "project_id_snapshot"):
        op.add_column("chat_messages", sa.Column("project_id_snapshot", sa.String(length=36), nullable=True))
    if not _has_column("chat_messages", "project_name_snapshot"):
        op.add_column("chat_messages", sa.Column("project_name_snapshot", sa.String(length=255), nullable=True))
    if _has_column("chat_messages", "project_id_snapshot") and not _has_index(
        "chat_messages", op.f("ix_chat_messages_project_id_snapshot")
    ):
        op.create_index(op.f("ix_chat_messages_project_id_snapshot"), "chat_messages", ["project_id_snapshot"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_messages_project_id_snapshot"), table_name="chat_messages")
    op.drop_column("chat_messages", "project_name_snapshot")
    op.drop_column("chat_messages", "project_id_snapshot")

    op.drop_constraint(None, "chat_sessions", type_="foreignkey")
    op.drop_index(op.f("ix_chat_sessions_project_id"), table_name="chat_sessions")
    op.drop_column("chat_sessions", "project_id")

    op.drop_constraint(None, "document_processing_jobs", type_="foreignkey")
    op.drop_index(op.f("ix_document_processing_jobs_project_id"), table_name="document_processing_jobs")
    op.drop_column("document_processing_jobs", "cancellation_requested")
    op.drop_column("document_processing_jobs", "progress_json")
    op.drop_column("document_processing_jobs", "project_id")

    op.drop_constraint(None, "documents", type_="foreignkey")
    op.drop_index(op.f("ix_documents_project_id"), table_name="documents")
    op.drop_column("documents", "processing_progress_json")
    op.drop_column("documents", "parser_metadata_json")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "project_id")

    op.drop_index(op.f("ix_project_memberships_created_by_user_id"), table_name="project_memberships")
    op.drop_index(op.f("ix_project_memberships_is_active"), table_name="project_memberships")
    op.drop_index(op.f("ix_project_memberships_user_id"), table_name="project_memberships")
    op.drop_index(op.f("ix_project_memberships_project_id"), table_name="project_memberships")
    op.drop_table("project_memberships")

    op.drop_index(op.f("ix_projects_created_by_user_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_is_active"), table_name="projects")
    op.drop_index(op.f("ix_projects_slug"), table_name="projects")
    op.drop_table("projects")

    sa.Enum(name="projectmembershiproleenum").drop(op.get_bind(), checkfirst=True)
