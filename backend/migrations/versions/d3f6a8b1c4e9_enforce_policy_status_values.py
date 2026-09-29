"""Enforce approved policy status values.

Revision ID: d3f6a8b1c4e9
Revises: e7c4a9b2d6f1
Create Date: 2026-07-23 08:45:00.000000

"""

from alembic import op

revision = "d3f6a8b1c4e9"
down_revision = "e7c4a9b2d6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("policies", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_policies_status",
            "status IN ('draft', 'active', 'inactive', 'revoked')",
        )


def downgrade() -> None:
    with op.batch_alter_table("policies", schema=None) as batch_op:
        batch_op.drop_constraint("ck_policies_status", type_="check")
