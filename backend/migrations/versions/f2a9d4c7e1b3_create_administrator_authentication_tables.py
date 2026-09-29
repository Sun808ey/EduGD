"""Create administrator authentication tables.

Revision ID: f2a9d4c7e1b3
Revises: c6f8a2d4e7b1
Create Date: 2026-07-19 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f2a9d4c7e1b3"
down_revision = "c6f8a2d4e7b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "administrators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("administrator_uuid", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_verifier", sa.String(length=512), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "failed_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("lock_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(display_name) BETWEEN 1 AND 120",
            name="ck_administrators_display_name_bounded",
        ),
        sa.CheckConstraint(
            "failed_attempts BETWEEN 0 AND 5",
            name="ck_administrators_failed_attempts",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND failed_attempts BETWEEN 0 AND 4 AND "
            "lock_expires_at IS NULL AND disabled_at IS NULL) OR "
            "(status = 'locked' AND failed_attempts = 5 AND "
            "lock_expires_at IS NOT NULL AND lock_expires_at > updated_at AND "
            "disabled_at IS NULL) OR "
            "(status = 'disabled' AND lock_expires_at IS NULL AND "
            "disabled_at IS NOT NULL)",
            name="ck_administrators_lifecycle",
        ),
        sa.CheckConstraint(
            "length(password_verifier) BETWEEN 1 AND 512 AND "
            "password_verifier LIKE 'scrypt:%'",
            name="ck_administrators_password_verifier",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'locked')",
            name="ck_administrators_status",
        ),
        sa.CheckConstraint(
            "length(username) BETWEEN 3 AND 64 AND username = lower(username)",
            name="ck_administrators_username_bounded",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "administrator_uuid",
            name="uq_administrators_uuid",
        ),
        sa.UniqueConstraint("username", name="uq_administrators_username"),
    )
    with op.batch_alter_table("administrators", schema=None) as batch_op:
        batch_op.create_index(
            "ix_administrators_status",
            ["status"],
            unique=False,
        )

    op.create_table(
        "administrator_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("administrator_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=64), nullable=False),
        sa.Column("granted_by_administrator_id", sa.Integer(), nullable=True),
        sa.Column("trusted_operator_subject", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(granted_by_administrator_id IS NOT NULL AND "
            "trusted_operator_subject IS NULL) OR "
            "(granted_by_administrator_id IS NULL AND "
            "trusted_operator_subject IS NOT NULL)",
            name="ck_administrator_permissions_grant_actor",
        ),
        sa.CheckConstraint(
            "trusted_operator_subject IS NULL OR "
            "length(trusted_operator_subject) BETWEEN 1 AND 255",
            name="ck_administrator_permissions_operator_bounded",
        ),
        sa.CheckConstraint(
            "permission IN ('administrator.manage', "
            "'enrollment_token.issue', 'enrollment_token.revoke')",
            name="ck_administrator_permissions_permission",
        ),
        sa.CheckConstraint(
            "length(reason) BETWEEN 1 AND 512",
            name="ck_administrator_permissions_reason_bounded",
        ),
        sa.ForeignKeyConstraint(
            ["administrator_id"],
            ["administrators.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_administrator_id"],
            ["administrators.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "administrator_id",
            "permission",
            name="uq_administrator_permissions_administrator_permission",
        ),
    )
    with op.batch_alter_table(
        "administrator_permissions",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            "ix_administrator_permissions_administrator",
            ["administrator_id"],
            unique=False,
        )

    op.create_table(
        "administrator_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("administrator_id", sa.Integer(), nullable=False),
        sa.Column("jti_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column(
            "source_address_pseudonym",
            sa.LargeBinary(length=32),
            nullable=True,
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_administrator_id", sa.Integer(), nullable=True),
        sa.Column(
            "revoked_by_operator_subject",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("revocation_reason", sa.String(length=512), nullable=True),
        sa.CheckConstraint(
            "expires_at > issued_at",
            name="ck_administrator_sessions_expiry",
        ),
        sa.CheckConstraint(
            "length(jti_digest) = 32",
            name="ck_administrator_sessions_jti_digest_length",
        ),
        sa.CheckConstraint(
            "(revoked_by_operator_subject IS NULL OR "
            "length(revoked_by_operator_subject) BETWEEN 1 AND 255) AND "
            "(revocation_reason IS NULL OR "
            "length(revocation_reason) BETWEEN 1 AND 512)",
            name="ck_administrator_sessions_revocation_metadata_bounded",
        ),
        sa.CheckConstraint(
            "(revoked_at IS NULL AND revoked_by_administrator_id IS NULL AND "
            "revoked_by_operator_subject IS NULL AND revocation_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_at >= issued_at AND "
            "revocation_reason IS NOT NULL AND "
            "((revoked_by_administrator_id IS NOT NULL AND "
            "revoked_by_operator_subject IS NULL) OR "
            "(revoked_by_administrator_id IS NULL AND "
            "revoked_by_operator_subject IS NOT NULL)))",
            name="ck_administrator_sessions_revocation_state",
        ),
        sa.CheckConstraint(
            "source_address_pseudonym IS NULL OR "
            "length(source_address_pseudonym) = 32",
            name="ck_administrator_sessions_source_pseudonym_length",
        ),
        sa.ForeignKeyConstraint(
            ["administrator_id"],
            ["administrators.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_administrator_id"],
            ["administrators.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "jti_digest",
            name="uq_administrator_sessions_jti_digest",
        ),
    )
    with op.batch_alter_table("administrator_sessions", schema=None) as batch_op:
        batch_op.create_index(
            "ix_administrator_sessions_administrator_expires",
            ["administrator_id", "expires_at"],
            unique=False,
        )

    op.create_table(
        "administrator_authentication_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("administrator_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("failure_class", sa.String(length=64), nullable=True),
        sa.Column(
            "source_address_pseudonym",
            sa.LargeBinary(length=32),
            nullable=True,
        ),
        sa.Column("acting_administrator_id", sa.Integer(), nullable=True),
        sa.Column("trusted_operator_subject", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "acting_administrator_id IS NULL OR trusted_operator_subject IS NULL",
            name="ck_administrator_authentication_events_actor",
        ),
        sa.CheckConstraint(
            "category IN ('bootstrap', 'login_succeeded', 'login_failed', "
            "'account_locked', 'account_unlocked', 'password_reset', 'logout', "
            "'session_revoked', 'account_disabled', 'permission_granted', "
            "'permission_revoked', 'authorization_failed')",
            name="ck_administrator_authentication_events_category",
        ),
        sa.CheckConstraint(
            "failure_class IS NULL OR length(failure_class) BETWEEN 1 AND 64",
            name="ck_administrator_authentication_events_failure_bounded",
        ),
        sa.CheckConstraint(
            "(trusted_operator_subject IS NULL OR "
            "length(trusted_operator_subject) BETWEEN 1 AND 255) AND "
            "(reason IS NULL OR length(reason) BETWEEN 1 AND 512)",
            name="ck_administrator_authentication_events_metadata_bounded",
        ),
        sa.CheckConstraint(
            "source_address_pseudonym IS NULL OR "
            "length(source_address_pseudonym) = 32",
            name="ck_administrator_authentication_events_source_pseudonym_length",
        ),
        sa.ForeignKeyConstraint(
            ["acting_administrator_id"],
            ["administrators.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["administrator_id"],
            ["administrators.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["administrator_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_uuid",
            name="uq_administrator_authentication_events_uuid",
        ),
    )
    with op.batch_alter_table(
        "administrator_authentication_events",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            "ix_administrator_authentication_events_administrator_created",
            ["administrator_id", "created_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_administrator_authentication_events_category_created",
            ["category", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "administrator_authentication_events",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            "ix_administrator_authentication_events_category_created"
        )
        batch_op.drop_index(
            "ix_administrator_authentication_events_administrator_created"
        )
    op.drop_table("administrator_authentication_events")

    with op.batch_alter_table("administrator_sessions", schema=None) as batch_op:
        batch_op.drop_index("ix_administrator_sessions_administrator_expires")
    op.drop_table("administrator_sessions")

    with op.batch_alter_table(
        "administrator_permissions",
        schema=None,
    ) as batch_op:
        batch_op.drop_index("ix_administrator_permissions_administrator")
    op.drop_table("administrator_permissions")

    with op.batch_alter_table("administrators", schema=None) as batch_op:
        batch_op.drop_index("ix_administrators_status")
    op.drop_table("administrators")
