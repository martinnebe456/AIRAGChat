"""embedding profiles and reindex runs"""

from __future__ import annotations

from alembic import op

revision = "20260225_000002"
down_revision = "20260225_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import models  # noqa: F401
    from app.db.base import Base

    # Create only missing tables introduced by newer metadata.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    op.drop_table("embedding_reindex_run_items")
    op.drop_table("embedding_reindex_runs")
    op.drop_table("embedding_profiles")

