"""Add authenticated offline device audit ingestion.

Revision ID: f8c2d5a7b9e1
Revises: e4a1b7c9d2f6
Create Date: 2026-09-20 16:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "f8c2d5a7b9e1"
down_revision = "e4a1b7c9d2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_audit_chain_heads",
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("last_sequence", sa.BigInteger(), nullable=False),
        sa.Column("head_event_hash", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "last_sequence >= 1", name="ck_device_audit_chain_heads_sequence"
        ),
        sa.CheckConstraint(
            "length(head_event_hash) = 32", name="ck_device_audit_chain_heads_hash"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("device_id"),
    )
    op.create_table(
        "device_audit_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("first_sequence", sa.BigInteger(), nullable=False),
        sa.Column("last_sequence", sa.BigInteger(), nullable=False),
        sa.Column("previous_head", sa.LargeBinary(32), nullable=True),
        sa.Column("final_head", sa.LargeBinary(32), nullable=False),
        sa.Column("signature_algorithm", sa.String(32), nullable=False),
        sa.Column("signature", sa.LargeBinary(), nullable=False),
        sa.Column("content_hash", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "first_sequence >= 1", name="ck_device_audit_batches_first_sequence"
        ),
        sa.CheckConstraint(
            "last_sequence >= first_sequence",
            name="ck_device_audit_batches_sequence_range",
        ),
        sa.CheckConstraint(
            "previous_head IS NULL OR length(previous_head) = 32",
            name="ck_device_audit_batches_previous_head",
        ),
        sa.CheckConstraint(
            "length(final_head) = 32", name="ck_device_audit_batches_final_head"
        ),
        sa.CheckConstraint(
            "length(content_hash) = 32", name="ck_device_audit_batches_content_hash"
        ),
        sa.CheckConstraint(
            "signature_algorithm IN ('ECDSA_P256_SHA256', 'RSA_2048_SHA256')",
            name="ck_device_audit_batches_signature_algorithm",
        ),
        sa.CheckConstraint(
            "length(signature) BETWEEN 64 AND 512",
            name="ck_device_audit_batches_signature_length",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["credential_id"], ["device_credentials.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("batch_uuid", name="uq_device_audit_batches_uuid"),
        sa.UniqueConstraint(
            "device_id",
            "first_sequence",
            "last_sequence",
            name="uq_device_audit_batches_device_sequence_range",
        ),
    )
    op.create_index(
        "ix_device_audit_batches_device_received",
        "device_audit_batches",
        ["device_id", "received_at"],
    )
    op.create_table(
        "device_security_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("elapsed_realtime_ms", sa.BigInteger(), nullable=False),
        sa.Column("boot_count", sa.Integer(), nullable=False),
        sa.Column("event_code", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("policy_uuid", sa.Uuid(), nullable=True),
        sa.Column("revision_uuid", sa.Uuid(), nullable=True),
        sa.Column("rule_id", sa.String(64), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("previous_event_hash", sa.LargeBinary(32), nullable=True),
        sa.Column("event_hash", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_device_security_events_sequence"),
        sa.CheckConstraint(
            "elapsed_realtime_ms >= 0", name="ck_device_security_events_elapsed"
        ),
        sa.CheckConstraint(
            "boot_count >= 0", name="ck_device_security_events_boot_count"
        ),
        sa.CheckConstraint(
            "previous_event_hash IS NULL OR length(previous_event_hash) = 32",
            name="ck_device_security_events_previous_hash",
        ),
        sa.CheckConstraint(
            "length(event_hash) = 32", name="ck_device_security_events_hash"
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["device_audit_batches.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_uuid", name="uq_device_security_events_uuid"),
        sa.UniqueConstraint(
            "device_id", "sequence", name="uq_device_security_events_device_sequence"
        ),
        sa.UniqueConstraint("event_hash", name="uq_device_security_events_hash"),
    )
    op.create_index(
        "ix_device_security_events_device_occurred",
        "device_security_events",
        ["device_id", "occurred_at"],
    )
    op.create_index(
        "ix_device_security_events_code_occurred",
        "device_security_events",
        ["event_code", "occurred_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "device_audit_chain_heads",
            "device_audit_batches",
            "device_security_events",
        ):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM PUBLIC")
            op.execute(
                f"""DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM authenticated;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM service_role;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM edug_runtime;
                END IF;
                END $$"""
            )
        op.execute(
            """CREATE FUNCTION edug_reject_device_audit_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'device audit evidence is immutable'; END;
            $$ LANGUAGE plpgsql"""
        )
        for table in ("device_audit_batches", "device_security_events"):
            op.execute(
                f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION edug_reject_device_audit_mutation()"
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("device_security_events", "device_audit_batches"):
            op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute("DROP FUNCTION edug_reject_device_audit_mutation()")
    op.drop_index(
        "ix_device_security_events_code_occurred", table_name="device_security_events"
    )
    op.drop_index(
        "ix_device_security_events_device_occurred", table_name="device_security_events"
    )
    op.drop_table("device_security_events")
    op.drop_index(
        "ix_device_audit_batches_device_received", table_name="device_audit_batches"
    )
    op.drop_table("device_audit_batches")
    op.drop_table("device_audit_chain_heads")
