"""Add privacy-minimised audit records for asset correction and redaction.
Revision ID: c3f7a2d9e1b4
Revises: b1c4e7a9d2f6
"""

import sqlalchemy as sa
from alembic import op

revision = "c3f7a2d9e1b4"
down_revision = "b1c4e7a9d2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_asset_change_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("administrator_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["administrator_id"], ["administrators.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_uuid", name="uq_device_asset_change_events_uuid"),
        sa.CheckConstraint(
            "operation IN ('corrected', 'retention_redacted')",
            name="ck_device_asset_change_events_operation",
        ),
        sa.CheckConstraint(
            "length(reason) BETWEEN 1 AND 512",
            name="ck_device_asset_change_events_reason",
        ),
    )
    op.create_index("ix_device_asset_change_events_created", "device_asset_change_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_device_asset_change_events_created", table_name="device_asset_change_events")
    op.drop_table("device_asset_change_events")
