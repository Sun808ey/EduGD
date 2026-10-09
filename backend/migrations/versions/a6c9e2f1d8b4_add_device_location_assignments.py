"""Create device class and department assignment history.

Revision ID: a6c9e2f1d8b4
Revises: f5a9c3e1b7d2
"""

import sqlalchemy as sa
from alembic import op

revision = "a6c9e2f1d8b4"
down_revision = "f5a9c3e1b7d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_location_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_uuid", sa.Uuid(), nullable=False),
        sa.Column(
            "device_id",
            sa.Integer(),
            sa.ForeignKey("devices.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_name", sa.String(120), nullable=False),
        sa.Column("responsible_officer", sa.String(120), nullable=False),
        sa.Column("assigned_at", sa.Date(), nullable=False),
        sa.Column("expected_return_date", sa.Date(), nullable=True),
        sa.Column("returned_at", sa.Date(), nullable=True),
        sa.Column("issue_condition", sa.String(80), nullable=False),
        sa.Column("return_condition", sa.String(80), nullable=True),
        sa.Column(
            "recorded_by_administrator_id",
            sa.Integer(),
            sa.ForeignKey("administrators.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "assignment_uuid", name="uq_device_location_assignments_uuid"
        ),
        sa.CheckConstraint(
            "target_type IN ('class', 'department')",
            name="ck_device_location_assignments_target_type",
        ),
        sa.CheckConstraint(
            "length(target_name) BETWEEN 1 AND 120",
            name="ck_device_location_assignments_target_name",
        ),
        sa.CheckConstraint(
            "length(responsible_officer) BETWEEN 1 AND 120",
            name="ck_device_location_assignments_officer",
        ),
        sa.CheckConstraint(
            "length(issue_condition) BETWEEN 1 AND 80",
            name="ck_device_location_assignments_issue_condition",
        ),
        sa.CheckConstraint(
            "return_condition IS NULL OR length(return_condition) BETWEEN 1 AND 80",
            name="ck_device_location_assignments_return_condition",
        ),
        sa.CheckConstraint(
            "expected_return_date IS NULL OR expected_return_date >= assigned_at",
            name="ck_device_location_assignments_expected_return",
        ),
        sa.CheckConstraint(
            "returned_at IS NULL OR returned_at >= assigned_at",
            name="ck_device_location_assignments_returned",
        ),
    )
    op.create_index(
        "uq_device_location_assignments_active_device",
        "device_location_assignments",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
        sqlite_where=sa.text("returned_at IS NULL"),
    )
    op.create_index(
        "ix_device_location_assignments_device_assigned",
        "device_location_assignments",
        ["device_id", "assigned_at"],
    )


def downgrade() -> None:
    op.drop_table("device_location_assignments")
