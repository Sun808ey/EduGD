"""Admit API 29–36 and suspend historical API 21–28 devices.

Revision ID: c7e5a9d2f4b8
Revises: a6d4e8f2b1c7
"""

import sqlalchemy as sa
from alembic import op

revision = "c7e5a9d2f4b8"
down_revision = "a6d4e8f2b1c7"
branch_labels = None
depends_on = None

ANDROID_API_MATCH = " OR ".join(
    f"(android_version = '{version}' AND api_level = {level})"
    for level, version in (
        (21, "5.0"),
        (22, "5.1"),
        (23, "6.0"),
        (24, "7.0"),
        (25, "7.1"),
        (26, "8.0"),
        (27, "8.1"),
        (28, "9"),
        (29, "10"),
        (30, "11"),
        (31, "12"),
        (32, "12L"),
        (33, "13"),
        (34, "14"),
        (35, "15"),
        (36, "16"),
    )
)
LEGACY_API_MATCH = " OR ".join(ANDROID_API_MATCH.split(" OR ")[:9])


def upgrade() -> None:
    # Preserve historical rows and evidence; they can no longer be active.
    # The old enrollment protocol has no independent physical certification.
    op.execute(
        sa.text("UPDATE devices SET status = 'suspended' WHERE status = 'active'")
    )
    with op.batch_alter_table("devices") as batch:
        batch.drop_constraint("ck_devices_android_api_match", type_="check")
        batch.drop_constraint("ck_devices_api_level_supported", type_="check")
        batch.create_check_constraint(
            "ck_devices_api_level_supported", "api_level BETWEEN 21 AND 36"
        )
        batch.create_check_constraint("ck_devices_android_api_match", ANDROID_API_MATCH)
        batch.create_check_constraint(
            "ck_devices_active_api_supported",
            "status <> 'active' OR api_level BETWEEN 29 AND 36",
        )
    with op.batch_alter_table("device_registration_events") as batch:
        batch.drop_constraint(
            "ck_device_registration_events_reported_api_level", type_="check"
        )
        batch.drop_constraint(
            "ck_device_registration_events_stored_api_level", type_="check"
        )
        batch.create_check_constraint(
            "ck_device_registration_events_reported_api_level",
            "reported_api_level BETWEEN 21 AND 36",
        )
        batch.create_check_constraint(
            "ck_device_registration_events_stored_api_level",
            "stored_api_level BETWEEN 21 AND 36",
        )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM devices WHERE api_level > 29")):
        raise RuntimeError("cannot downgrade while Android API 30–36 devices exist")
    with op.batch_alter_table("device_registration_events") as batch:
        batch.drop_constraint(
            "ck_device_registration_events_reported_api_level", type_="check"
        )
        batch.drop_constraint(
            "ck_device_registration_events_stored_api_level", type_="check"
        )
        batch.create_check_constraint(
            "ck_device_registration_events_reported_api_level",
            "reported_api_level BETWEEN 21 AND 29",
        )
        batch.create_check_constraint(
            "ck_device_registration_events_stored_api_level",
            "stored_api_level BETWEEN 21 AND 29",
        )
    with op.batch_alter_table("devices") as batch:
        batch.drop_constraint("ck_devices_active_api_supported", type_="check")
        batch.drop_constraint("ck_devices_android_api_match", type_="check")
        batch.drop_constraint("ck_devices_api_level_supported", type_="check")
        batch.create_check_constraint(
            "ck_devices_api_level_supported", "api_level BETWEEN 21 AND 29"
        )
        batch.create_check_constraint("ck_devices_android_api_match", LEGACY_API_MATCH)
