"""Create administrator-managed incident records.

Revision ID: b1c4e7a9d2f6
Revises: a6c9e2f1d8b4
"""

import sqlalchemy as sa
from alembic import op

revision = "b1c4e7a9d2f6"
down_revision = "a6c9e2f1d8b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_uuid", sa.Uuid(), nullable=False),
        sa.Column("incident_number", sa.String(32), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("incident_type", sa.String(48), nullable=False),
        sa.Column("description", sa.String(2048), nullable=False),
        sa.Column("reported_by", sa.String(120), nullable=False),
        sa.Column(
            "reported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("status", sa.String(16), server_default="OPEN", nullable=False),
        sa.Column("action_taken", sa.String(2048), nullable=True),
        sa.Column("responsible_person", sa.String(120), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_administrator_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_administrator_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["created_by_administrator_id"], ["administrators.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_administrator_id"], ["administrators.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("incident_uuid", name="uq_incidents_uuid"),
        sa.UniqueConstraint("incident_number", name="uq_incidents_number"),
        sa.CheckConstraint(
            "incident_type IN ('device_missing', 'unauthorised_application', "
            "'policy_application_failure', 'wrong_assignment', 'device_offline', "
            "'device_damaged', 'kiosk_bypass_attempt', 'enrolment_token_exposed', "
            "'administrator_anomaly', 'other')",
            name="ck_incidents_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'UNDER_REVIEW', 'ACTION_TAKEN', 'CLOSED')",
            name="ck_incidents_status",
        ),
        sa.CheckConstraint(
            "length(description) BETWEEN 1 AND 2048",
            name="ck_incidents_description_bounded",
        ),
    )
    op.create_index("ix_incidents_reported_at", "incidents", ["reported_at"])
    op.create_index("ix_incidents_device_status", "incidents", ["device_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_incidents_device_status", table_name="incidents")
    op.drop_index("ix_incidents_reported_at", table_name="incidents")
    op.drop_table("incidents")
