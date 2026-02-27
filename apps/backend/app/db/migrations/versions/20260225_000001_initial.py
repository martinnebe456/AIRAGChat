"""initial schema"""

from __future__ import annotations

from alembic import op

revision = "20260225_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import models  # noqa: F401
    from app.db.base import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.db import models  # noqa: F401
    from app.db.base import Base

    Base.metadata.drop_all(bind=op.get_bind())

