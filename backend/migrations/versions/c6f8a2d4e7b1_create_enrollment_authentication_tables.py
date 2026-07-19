"""Create device enrollment authentication tables.

Revision ID: c6f8a2d4e7b1
Revises: b4e7c1d3f5a9
Create Date: 2026-07-19 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c6f8a2d4e7b1"
down_revision = "b4e7c1d3f5a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrollment_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_uuid", sa.Uuid(), nullable=False),
        sa.Column("verifier", sa.LargeBinary(length=32), nullable=False),
        sa.Column(
            "pepper_version",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("bound_device_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "failed_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_by_device_id", sa.Integer(), nullable=True),
        sa.Column("issued_by", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=255), nullable=True),
        sa.Column("revocation_reason", sa.String(length=512), nullable=True),
        sa.CheckConstraint(
            "(status = 'consumed' AND consumed_at IS NOT NULL AND "
            "consumed_by_device_id IS NOT NULL) OR "
            "(status <> 'consumed' AND consumed_at IS NULL AND "
            "consumed_by_device_id IS NULL)",
            name="ck_enrollment_tokens_consumption_state",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_enrollment_tokens_expiry",
        ),
        sa.CheckConstraint(
            "failed_attempts BETWEEN 0 AND 5",
            name="ck_enrollment_tokens_failed_attempts",
        ),
        sa.CheckConstraint(
            "pepper_version >= 1",
            name="ck_enrollment_tokens_pepper_version",
        ),
        sa.CheckConstraint(
            "(status = 'revoked' AND revoked_at IS NOT NULL AND "
            "revoked_by IS NOT NULL AND revocation_reason IS NOT NULL) OR "
            "(status <> 'revoked' AND revoked_at IS NULL AND "
            "revoked_by IS NULL AND revocation_reason IS NULL)",
            name="ck_enrollment_tokens_revocation_state",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'consumed', 'revoked', 'expired', 'locked')",
            name="ck_enrollment_tokens_status",
        ),
        sa.ForeignKeyConstraint(
            ["bound_device_id"],
            ["devices.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["consumed_by_device_id"],
            ["devices.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_uuid", name="uq_enrollment_tokens_uuid"),
    )
    with op.batch_alter_table("enrollment_tokens", schema=None) as batch_op:
        batch_op.create_index(
            "ix_enrollment_tokens_bound_device",
            ["bound_device_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_enrollment_tokens_status_expires",
            ["status", "expires_at"],
            unique=False,
        )

    op.create_table(
        "device_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credential_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_token_id", sa.Integer(), nullable=True),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("public_key_der", sa.LargeBinary(), nullable=False),
        sa.Column(
            "public_key_fingerprint",
            sa.LargeBinary(length=32),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=255), nullable=True),
        sa.Column("revocation_reason", sa.String(length=512), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "algorithm IN ('RSA_2048_SHA256')",
            name="ck_device_credentials_algorithm",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND revoked_at IS NULL AND revoked_by IS NULL "
            "AND revocation_reason IS NULL AND superseded_at IS NULL AND "
            "superseded_by_id IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL AND "
            "revoked_by IS NOT NULL AND revocation_reason IS NOT NULL AND "
            "superseded_at IS NULL AND superseded_by_id IS NULL) OR "
            "(status = 'superseded' AND revoked_at IS NULL AND "
            "revoked_by IS NULL AND revocation_reason IS NULL AND "
            "superseded_at IS NOT NULL AND superseded_by_id IS NOT NULL)",
            name="ck_device_credentials_lifecycle",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'superseded')",
            name="ck_device_credentials_status",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_token_id"],
            ["enrollment_tokens.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["device_credentials.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "credential_uuid",
            name="uq_device_credentials_uuid",
        ),
        sa.UniqueConstraint(
            "public_key_fingerprint",
            name="uq_device_credentials_public_key_fingerprint",
        ),
    )
    with op.batch_alter_table("device_credentials", schema=None) as batch_op:
        batch_op.create_index(
            "ix_device_credentials_device_status",
            ["device_id", "status"],
            unique=False,
        )
        batch_op.create_index(
            "uq_device_credentials_active_device",
            ["device_id"],
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
            sqlite_where=sa.text("status = 'active'"),
        )

    op.create_table(
        "device_request_nonces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("nonce_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "expires_at > observed_at",
            name="ck_device_request_nonces_expiry",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["device_credentials.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "credential_id",
            "nonce_hash",
            name="uq_device_request_nonces_credential_hash",
        ),
    )
    with op.batch_alter_table("device_request_nonces", schema=None) as batch_op:
        batch_op.create_index(
            "ix_device_request_nonces_expires_at",
            ["expires_at"],
            unique=False,
        )

    op.create_table(
        "device_enrollment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("token_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("failure_class", sa.String(length=64), nullable=True),
        sa.Column("administrator_subject", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column(
            "public_key_fingerprint",
            sa.LargeBinary(length=32),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('token_issued', 'token_revoked', "
            "'enrollment_succeeded', 'enrollment_failed', "
            "'credential_rotated', 'credential_revoked', "
            "'authentication_failed', 'legacy_authentication_used', "
            "'legacy_authentication_disabled')",
            name="ck_device_enrollment_events_category",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["device_credentials.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["token_id"],
            ["enrollment_tokens.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_uuid",
            name="uq_device_enrollment_events_uuid",
        ),
    )
    with op.batch_alter_table("device_enrollment_events", schema=None) as batch_op:
        batch_op.create_index(
            "ix_device_enrollment_events_credential_created",
            ["credential_id", "created_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_device_enrollment_events_device_created",
            ["device_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("device_enrollment_events", schema=None) as batch_op:
        batch_op.drop_index("ix_device_enrollment_events_device_created")
        batch_op.drop_index("ix_device_enrollment_events_credential_created")
    op.drop_table("device_enrollment_events")

    with op.batch_alter_table("device_request_nonces", schema=None) as batch_op:
        batch_op.drop_index("ix_device_request_nonces_expires_at")
    op.drop_table("device_request_nonces")

    with op.batch_alter_table("device_credentials", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_device_credentials_active_device",
            postgresql_where=sa.text("status = 'active'"),
            sqlite_where=sa.text("status = 'active'"),
        )
        batch_op.drop_index("ix_device_credentials_device_status")
    op.drop_table("device_credentials")

    with op.batch_alter_table("enrollment_tokens", schema=None) as batch_op:
        batch_op.drop_index("ix_enrollment_tokens_status_expires")
        batch_op.drop_index("ix_enrollment_tokens_bound_device")
    op.drop_table("enrollment_tokens")
