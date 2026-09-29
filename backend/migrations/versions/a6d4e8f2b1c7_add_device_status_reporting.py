"""Add device check-ins and policy application acknowledgements.

Revision ID: a6d4e8f2b1c7
Revises: f8c2d5a7b9e1
Create Date: 2026-09-20 18:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "a6d4e8f2b1c7"
down_revision = "f8c2d5a7b9e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_check_ins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_in_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("elapsed_realtime_ms", sa.BigInteger(), nullable=False),
        sa.Column("boot_count", sa.Integer(), nullable=False),
        sa.Column("dpc_version", sa.Integer(), nullable=False),
        sa.Column("android_version", sa.String(32), nullable=False),
        sa.Column("api_level", sa.Integer(), nullable=False),
        sa.Column("security_patch", sa.Date(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("current_policy_uuid", sa.Uuid(), nullable=True),
        sa.Column("current_revision_uuid", sa.Uuid(), nullable=True),
        sa.Column("policy_status", sa.String(32), nullable=False),
        sa.Column("enforcement_healthy", sa.Boolean(), nullable=False),
        sa.Column("queued_event_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.LargeBinary(32), nullable=False),
        sa.CheckConstraint(
            "elapsed_realtime_ms >= 0", name="ck_device_check_ins_elapsed"
        ),
        sa.CheckConstraint("boot_count >= 0", name="ck_device_check_ins_boot_count"),
        sa.CheckConstraint("dpc_version >= 1", name="ck_device_check_ins_dpc_version"),
        sa.CheckConstraint(
            "api_level BETWEEN 29 AND 36", name="ck_device_check_ins_api_level"
        ),
        sa.CheckConstraint(
            "queued_event_count >= 0", name="ck_device_check_ins_queued_events"
        ),
        sa.CheckConstraint(
            "length(content_hash) = 32", name="ck_device_check_ins_content_hash"
        ),
        sa.CheckConstraint(
            "policy_status IN ('none', 'verified', 'applied', 'stale', 'recovery')",
            name="ck_device_check_ins_policy_status",
        ),
        sa.CheckConstraint(
            "(current_policy_uuid IS NULL) = (current_revision_uuid IS NULL)",
            name="ck_device_check_ins_policy_identity",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["credential_id"], ["device_credentials.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("check_in_uuid", name="uq_device_check_ins_uuid"),
    )
    op.create_index(
        "ix_device_check_ins_device_received",
        "device_check_ins",
        ["device_id", "received_at"],
    )
    op.create_table(
        "device_compliance_states",
        sa.Column("device_id", sa.Integer(), primary_key=True),
        sa.Column("last_check_in_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_boot_count", sa.Integer(), nullable=False),
        sa.Column("dpc_version", sa.Integer(), nullable=False),
        sa.Column("android_version", sa.String(32), nullable=False),
        sa.Column("api_level", sa.Integer(), nullable=False),
        sa.Column("security_patch", sa.Date(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("current_policy_uuid", sa.Uuid(), nullable=True),
        sa.Column("current_revision_uuid", sa.Uuid(), nullable=True),
        sa.Column("policy_status", sa.String(32), nullable=False),
        sa.Column("enforcement_healthy", sa.Boolean(), nullable=False),
        sa.Column("queued_event_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "last_boot_count >= 0", name="ck_device_compliance_states_boot_count"
        ),
        sa.CheckConstraint(
            "dpc_version >= 1", name="ck_device_compliance_states_dpc_version"
        ),
        sa.CheckConstraint(
            "api_level BETWEEN 29 AND 36", name="ck_device_compliance_states_api_level"
        ),
        sa.CheckConstraint(
            "queued_event_count >= 0", name="ck_device_compliance_states_queued_events"
        ),
        sa.CheckConstraint(
            "policy_status IN ('none', 'verified', 'applied', 'stale', 'recovery')",
            name="ck_device_compliance_states_policy_status",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["last_check_in_id"], ["device_check_ins.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "policy_application_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("acknowledgement_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("elapsed_realtime_ms", sa.BigInteger(), nullable=False),
        sa.Column("boot_count", sa.Integer(), nullable=False),
        sa.Column("policy_uuid", sa.Uuid(), nullable=True),
        sa.Column("revision_uuid", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.LargeBinary(32), nullable=False),
        sa.CheckConstraint(
            "elapsed_realtime_ms >= 0", name="ck_policy_application_events_elapsed"
        ),
        sa.CheckConstraint(
            "boot_count >= 0", name="ck_policy_application_events_boot_count"
        ),
        sa.CheckConstraint(
            "length(content_hash) = 32",
            name="ck_policy_application_events_content_hash",
        ),
        sa.CheckConstraint(
            "outcome IN ('verified', 'applied', 'failed', 'rejected', 'rolled_back', 'cleared')",
            name="ck_policy_application_events_outcome",
        ),
        sa.CheckConstraint(
            "(policy_uuid IS NULL) = (revision_uuid IS NULL)",
            name="ck_policy_application_events_identity",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["credential_id"], ["device_credentials.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "acknowledgement_uuid", name="uq_policy_application_events_uuid"
        ),
    )
    op.create_index(
        "ix_policy_application_events_device_received",
        "policy_application_events",
        ["device_id", "received_at"],
    )
    op.create_table(
        "device_policy_states",
        sa.Column("device_id", sa.Integer(), primary_key=True),
        sa.Column("last_event_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("policy_uuid", sa.Uuid(), nullable=True),
        sa.Column("revision_uuid", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["last_event_id"], ["policy_application_events.id"], ondelete="RESTRICT"
        ),
    )
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "device_check_ins",
            "device_compliance_states",
            "policy_application_events",
            "device_policy_states",
        ):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM PUBLIC")
            op.execute(
                f"""DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL PRIVILEGES ON TABLE {table} FROM anon; END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL PRIVILEGES ON TABLE {table} FROM authenticated; END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN REVOKE ALL PRIVILEGES ON TABLE {table} FROM service_role; END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN REVOKE ALL PRIVILEGES ON TABLE {table} FROM edug_runtime; END IF;
                END $$"""
            )
        op.execute(
            """CREATE FUNCTION edug_reject_device_status_evidence_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'device status evidence is immutable'; END; $$ LANGUAGE plpgsql"""
        )
        for table in ("device_check_ins", "policy_application_events"):
            op.execute(
                f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION edug_reject_device_status_evidence_mutation()"
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("policy_application_events", "device_check_ins"):
            op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute("DROP FUNCTION edug_reject_device_status_evidence_mutation()")
    op.drop_table("device_policy_states")
    op.drop_index(
        "ix_policy_application_events_device_received",
        table_name="policy_application_events",
    )
    op.drop_table("policy_application_events")
    op.drop_table("device_compliance_states")
    op.drop_index("ix_device_check_ins_device_received", table_name="device_check_ins")
    op.drop_table("device_check_ins")
