"""Add authoritative Android API-level compatibility constraints.

Revision ID: 9d2f4a6c8e10
Revises: 7c91b8e2d4a6
Create Date: 2026-07-18 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9d2f4a6c8e10"
down_revision = "7c91b8e2d4a6"
branch_labels = None
depends_on = None

ANDROID_API_MATCH = (
    "(android_version = '5.0' AND api_level = 21) OR "
    "(android_version = '5.1' AND api_level = 22) OR "
    "(android_version = '6.0' AND api_level = 23) OR "
    "(android_version = '7.0' AND api_level = 24) OR "
    "(android_version = '7.1' AND api_level = 25) OR "
    "(android_version = '8.0' AND api_level = 26) OR "
    "(android_version = '8.1' AND api_level = 27) OR "
    "(android_version = '9' AND api_level = 28) OR "
    "(android_version = '10' AND api_level = 29)"
)


def upgrade() -> None:
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("api_level", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE devices SET api_level = CASE android_version "
            "WHEN '5.0' THEN 21 WHEN '5.1' THEN 22 "
            "WHEN '6.0' THEN 23 WHEN '7.0' THEN 24 "
            "WHEN '7.1' THEN 25 WHEN '8.0' THEN 26 "
            "WHEN '8.1' THEN 27 WHEN '9' THEN 28 "
            "WHEN '10' THEN 29 END"
        )
    )

    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.alter_column(
            "api_level",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_devices_api_level_supported",
            "api_level BETWEEN 21 AND 29",
        )
        batch_op.create_check_constraint(
            "ck_devices_android_api_match",
            ANDROID_API_MATCH,
        )


def downgrade() -> None:
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_devices_android_api_match",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_devices_api_level_supported",
            type_="check",
        )
        batch_op.drop_column("api_level")
