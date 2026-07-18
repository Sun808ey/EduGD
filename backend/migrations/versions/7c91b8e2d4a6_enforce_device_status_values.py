"""Enforce approved device status values.

Revision ID: 7c91b8e2d4a6
Revises: 3a6f4a9eb4f2
Create Date: 2026-07-18 15:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7c91b8e2d4a6"
down_revision = "3a6f4a9eb4f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_devices_status",
            "status IN ('active', 'suspended', 'retired')",
        )


def downgrade() -> None:
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.drop_constraint("ck_devices_status", type_="check")
