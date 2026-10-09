"""Add the school timetable timezone."""

import sqlalchemy as sa
from alembic import op

revision = "g1b2c3d4e5f6"
down_revision = "c3f7a2d9e1b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schools",
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Africa/Kampala"),
    )


def downgrade() -> None:
    op.drop_column("schools", "timezone")
