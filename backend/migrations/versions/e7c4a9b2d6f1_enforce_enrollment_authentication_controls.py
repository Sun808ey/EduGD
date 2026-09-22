"""Enforce enrollment authentication rollout controls.

Revision ID: e7c4a9b2d6f1
Revises: f2a9d4c7e1b3
Create Date: 2026-07-21 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e7c4a9b2d6f1"
down_revision = "f2a9d4c7e1b3"
branch_labels = None
depends_on = None

OLD_EVENT_CATEGORIES = (
    "'token_issued', 'token_revoked', 'enrollment_succeeded', "
    "'enrollment_failed', 'credential_rotated', 'credential_revoked', "
    "'authentication_failed', 'legacy_authentication_used', "
    "'legacy_authentication_disabled'"
)
NEW_EVENT_CATEGORIES = (
    "'token_issued', 'token_revoked', 'token_consumed', "
    "'enrollment_succeeded', 'enrollment_failed', 'credential_rotated', "
    "'credential_revoked', 'authentication_succeeded', "
    "'authentication_failed', 'legacy_authentication_used', "
    "'legacy_authentication_disabled'"
)
OLD_PERMISSIONS = (
    "'administrator.manage', 'enrollment_token.issue', 'enrollment_token.revoke'"
)
NEW_PERMISSIONS = (
    "'administrator.manage', 'enrollment_token.issue', "
    "'enrollment_token.revoke', 'device_credential.revoke'"
)


def upgrade() -> None:
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "legacy_enrollment_eligible",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            )
        )
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.alter_column(
            "legacy_enrollment_eligible",
            server_default=sa.false(),
        )

    with op.batch_alter_table("device_enrollment_events", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_device_enrollment_events_category",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_device_enrollment_events_category",
            f"category IN ({NEW_EVENT_CATEGORIES})",
        )
        batch_op.create_check_constraint(
            "ck_device_enrollment_events_fingerprint_length",
            "public_key_fingerprint IS NULL OR "
            "length(public_key_fingerprint) = 32",
        )

    with op.batch_alter_table("device_credentials", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_device_credentials_lifecycle",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_device_credentials_lifecycle",
            "(status = 'active' AND revoked_at IS NULL AND revoked_by IS NULL "
            "AND revocation_reason IS NULL AND superseded_at IS NULL AND "
            "superseded_by_id IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL AND "
            "revoked_by IS NOT NULL AND revocation_reason IS NOT NULL AND "
            "superseded_at IS NULL AND superseded_by_id IS NULL) OR "
            "(status = 'superseded' AND revoked_at IS NULL AND "
            "revoked_by IS NULL AND revocation_reason IS NULL AND "
            "superseded_at IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_device_credentials_public_key_length",
            "length(public_key_der) BETWEEN 1 AND 512",
        )
        batch_op.create_check_constraint(
            "ck_device_credentials_fingerprint_length",
            "length(public_key_fingerprint) = 32",
        )

    with op.batch_alter_table("enrollment_tokens", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_enrollment_tokens_verifier_length",
            "length(verifier) = 32",
        )

    with op.batch_alter_table("device_request_nonces", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_device_request_nonces_hash_length",
            "length(nonce_hash) = 32",
        )

    with op.batch_alter_table("administrator_permissions", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_administrator_permissions_permission",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_administrator_permissions_permission",
            f"permission IN ({NEW_PERMISSIONS})",
        )


def downgrade() -> None:
    with op.batch_alter_table("administrator_permissions", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_administrator_permissions_permission",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_administrator_permissions_permission",
            f"permission IN ({OLD_PERMISSIONS})",
        )

    with op.batch_alter_table("device_enrollment_events", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_device_enrollment_events_fingerprint_length",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_device_enrollment_events_category",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_device_enrollment_events_category",
            f"category IN ({OLD_EVENT_CATEGORIES})",
        )

    with op.batch_alter_table("device_credentials", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_device_credentials_fingerprint_length",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_device_credentials_public_key_length",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_device_credentials_lifecycle",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_device_credentials_lifecycle",
            "(status = 'active' AND revoked_at IS NULL AND revoked_by IS NULL "
            "AND revocation_reason IS NULL AND superseded_at IS NULL AND "
            "superseded_by_id IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL AND "
            "revoked_by IS NOT NULL AND revocation_reason IS NOT NULL AND "
            "superseded_at IS NULL AND superseded_by_id IS NULL) OR "
            "(status = 'superseded' AND revoked_at IS NULL AND "
            "revoked_by IS NULL AND revocation_reason IS NULL AND "
            "superseded_at IS NOT NULL AND superseded_by_id IS NOT NULL)",
        )

    with op.batch_alter_table("device_request_nonces", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_device_request_nonces_hash_length",
            type_="check",
        )

    with op.batch_alter_table("enrollment_tokens", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_enrollment_tokens_verifier_length",
            type_="check",
        )

    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.drop_column("legacy_enrollment_eligible")
