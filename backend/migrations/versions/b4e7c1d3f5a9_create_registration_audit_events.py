"""Create immutable device registration audit events.

Revision ID: b4e7c1d3f5a9
Revises: 9d2f4a6c8e10
Create Date: 2026-07-18 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4e7c1d3f5a9"
down_revision = "9d2f4a6c8e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_registration_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("stored_android_version", sa.String(length=32), nullable=False),
        sa.Column("stored_api_level", sa.Integer(), nullable=False),
        sa.Column("reported_android_version", sa.String(length=32), nullable=False),
        sa.Column("reported_api_level", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('registered', 'duplicate', "
            "'upgrade_requires_authentication', 'downgrade_rejected')",
            name="ck_device_registration_events_type",
        ),
        sa.CheckConstraint(
            "reported_api_level BETWEEN 21 AND 29",
            name="ck_device_registration_events_reported_api_level",
        ),
        sa.CheckConstraint(
            "stored_api_level BETWEEN 21 AND 29",
            name="ck_device_registration_events_stored_api_level",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_uuid",
            name="uq_device_registration_events_uuid",
        ),
    )
    with op.batch_alter_table("device_registration_events", schema=None) as batch_op:
        batch_op.create_index(
            "ix_device_registration_events_device_created",
            ["device_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("device_registration_events", schema=None) as batch_op:
        batch_op.drop_index("ix_device_registration_events_device_created")
    op.drop_table("device_registration_events")
