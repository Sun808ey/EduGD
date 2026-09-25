"""Restrict newly active devices to Android API 29-35.

Revision ID: d1f7b3c9e5a2
Revises: c2f8a1b4d630
"""

import sqlalchemy as sa
from alembic import op

revision = "d1f7b3c9e5a2"
down_revision = "c2f8a1b4d630"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical API 36 rows remain readable, but cannot remain live.
    op.execute(
        sa.text(
            "UPDATE devices SET status = 'suspended' "
            "WHERE status = 'active' AND api_level = 36"
        )
    )
    with op.batch_alter_table("devices") as batch:
        batch.drop_constraint("ck_devices_active_api_supported", type_="check")
        batch.create_check_constraint(
            "ck_devices_active_api_supported",
            "status <> 'active' OR api_level BETWEEN 29 AND 35",
        )
    with op.batch_alter_table("device_credentials") as batch:
        batch.drop_constraint("ck_device_credentials_algorithm", type_="check")
        batch.create_check_constraint(
            "ck_device_credentials_algorithm",
            "algorithm IN ('ECDSA_P256_SHA256', 'RSA_2048_SHA256')",
        )
    connection = op.get_bind()
    for permission in (
        "administrator.manage",
        "enrollment_token.issue",
        "enrollment_token.revoke",
        "device_credential.revoke",
        "policy.assign",
        "device.control",
        "policy.manage",
    ):
        connection.execute(
            sa.text(
                "INSERT INTO administrator_permissions "
                "(administrator_id, permission, trusted_operator_subject, reason) "
                "SELECT id, :permission, :operator, :reason FROM administrators "
                "WHERE NOT EXISTS (SELECT 1 FROM administrator_permissions ap "
                "WHERE ap.administrator_id = administrators.id "
                "AND ap.permission = :permission)"
            ),
            {
                "permission": permission,
                "operator": "system:administrator-permission-migration",
                "reason": "all authenticated administrators retain full control access",
            },
        )


def downgrade() -> None:
    with op.batch_alter_table("devices") as batch:
        batch.drop_constraint("ck_devices_active_api_supported", type_="check")
        batch.create_check_constraint(
            "ck_devices_active_api_supported",
            "status <> 'active' OR api_level BETWEEN 29 AND 36",
        )