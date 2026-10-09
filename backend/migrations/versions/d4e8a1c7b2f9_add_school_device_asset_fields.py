"""Add school-owned device asset registration fields.

Revision ID: d4e8a1c7b2f9
Revises: c8d2e7f4a1b6
Create Date: 2026-10-05 17:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e8a1c7b2f9"
down_revision = "c8d2e7f4a1b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for _name, column in (
        ("asset_number", sa.Column("asset_number", sa.String(80), nullable=True)),
        ("manufacturer", sa.Column("manufacturer", sa.String(120), nullable=True)),
        ("model", sa.Column("model", sa.String(120), nullable=True)),
        ("serial_number", sa.Column("serial_number", sa.String(160), nullable=True)),
        ("date_received", sa.Column("date_received", sa.Date(), nullable=True)),
        ("condition", sa.Column("condition", sa.String(80), nullable=True)),
        ("department", sa.Column("department", sa.String(120), nullable=True)),
        (
            "asset_lifecycle_status",
            sa.Column("asset_lifecycle_status", sa.String(32), nullable=True),
        ),
        ("asset_notes", sa.Column("asset_notes", sa.String(512), nullable=True)),
    ):
        op.add_column("devices", column)
    with op.batch_alter_table("devices") as batch:
        batch.create_unique_constraint("uq_devices_asset_number", ["asset_number"])
        batch.create_unique_constraint("uq_devices_serial_number", ["serial_number"])


def downgrade() -> None:
    with op.batch_alter_table("devices") as batch:
        batch.drop_constraint("uq_devices_serial_number", type_="unique")
        batch.drop_constraint("uq_devices_asset_number", type_="unique")
    for name in (
        "asset_notes",
        "asset_lifecycle_status",
        "department",
        "condition",
        "date_received",
        "serial_number",
        "model",
        "manufacturer",
        "asset_number",
    ):
        op.drop_column("devices", name)
