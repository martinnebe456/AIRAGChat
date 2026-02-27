"""ingestion queue dispatch metadata"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260226_000004"
down_revision = "20260226_000003"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


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
    if not _has_column("document_processing_jobs", "dispatched_at"):
        op.add_column("document_processing_jobs", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("document_processing_jobs", "dispatched_by_user_id"):
        op.add_column("document_processing_jobs", sa.Column("dispatched_by_user_id", sa.String(length=36), nullable=True))
    if not _has_column("document_processing_jobs", "dispatch_trigger"):
        op.add_column("document_processing_jobs", sa.Column("dispatch_trigger", sa.String(length=64), nullable=True))
    if not _has_column("document_processing_jobs", "dispatch_batch_id"):
        op.add_column("document_processing_jobs", sa.Column("dispatch_batch_id", sa.String(length=64), nullable=True))

    if _has_column("document_processing_jobs", "dispatched_by_user_id") and not _has_index(
        "document_processing_jobs", op.f("ix_document_processing_jobs_dispatched_by_user_id")
    ):
        op.create_index(
            op.f("ix_document_processing_jobs_dispatched_by_user_id"),
            "document_processing_jobs",
            ["dispatched_by_user_id"],
            unique=False,
        )
    if _has_column("document_processing_jobs", "dispatch_batch_id") and not _has_index(
        "document_processing_jobs", op.f("ix_document_processing_jobs_dispatch_batch_id")
    ):
        op.create_index(
            op.f("ix_document_processing_jobs_dispatch_batch_id"),
            "document_processing_jobs",
            ["dispatch_batch_id"],
            unique=False,
        )
    if _has_column("document_processing_jobs", "dispatched_by_user_id") and not _fk_exists(
        "document_processing_jobs", ["dispatched_by_user_id"], "users"
    ):
        op.create_foreign_key(
            None,
            "document_processing_jobs",
            "users",
            ["dispatched_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint(None, "document_processing_jobs", type_="foreignkey")
    op.drop_index(op.f("ix_document_processing_jobs_dispatch_batch_id"), table_name="document_processing_jobs")
    op.drop_index(op.f("ix_document_processing_jobs_dispatched_by_user_id"), table_name="document_processing_jobs")
    op.drop_column("document_processing_jobs", "dispatch_batch_id")
    op.drop_column("document_processing_jobs", "dispatch_trigger")
    op.drop_column("document_processing_jobs", "dispatched_by_user_id")
    op.drop_column("document_processing_jobs", "dispatched_at")
