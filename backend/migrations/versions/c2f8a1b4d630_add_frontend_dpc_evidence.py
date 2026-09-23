"""Add frontend DPC evidence and policy-management permission.

Revision ID: c2f8a1b4d630
Revises: ab4e6f2c9d71
"""

import sqlalchemy as sa
from alembic import op


revision = "c2f8a1b4d630"
down_revision = "ab4e6f2c9d71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("administrator_permissions") as batch:
        batch.drop_constraint("ck_administrator_permissions_permission", type_="check")
        batch.create_check_constraint(
            "ck_administrator_permissions_permission",
            "permission IN ('administrator.manage','enrollment_token.issue',"
            "'enrollment_token.revoke','device_credential.revoke','policy.assign',"
            "'device.control','policy.manage')",
        )

    op.create_table(
        "device_web_filter_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("domain_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False, server_default="blocked"),
        sa.Column("policy_uuid", sa.Uuid(), nullable=False),
        sa.Column("revision_uuid", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_uuid", name="uq_device_web_filter_events_uuid"),
        sa.CheckConstraint("length(domain_hash) = 32", name="ck_device_web_filter_events_domain_hash"),
        sa.CheckConstraint("outcome = 'blocked'", name="ck_device_web_filter_events_outcome"),
    )
    op.create_index("ix_device_web_filter_events_device_observed", "device_web_filter_events", ["device_id", "observed_at"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE device_web_filter_events ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE device_web_filter_events FROM PUBLIC")
        op.execute("""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL PRIVILEGES ON TABLE device_web_filter_events FROM anon; END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL PRIVILEGES ON TABLE device_web_filter_events FROM authenticated; END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN REVOKE ALL PRIVILEGES ON TABLE device_web_filter_events FROM service_role; END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                GRANT SELECT, INSERT ON TABLE device_web_filter_events TO edug_runtime;
                CREATE POLICY edug_backend_runtime ON device_web_filter_events AS PERMISSIVE FOR ALL TO edug_runtime USING (true) WITH CHECK (true);
            END IF;
        END $$""")
        op.execute("""CREATE FUNCTION edug_reject_web_filter_event_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'web filter evidence is immutable'; END;
        $$ LANGUAGE plpgsql""")
        op.execute("CREATE TRIGGER trg_device_web_filter_events_immutable BEFORE UPDATE OR DELETE ON device_web_filter_events FOR EACH ROW EXECUTE FUNCTION edug_reject_web_filter_event_mutation()")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER trg_device_web_filter_events_immutable ON device_web_filter_events")
        op.execute("DROP FUNCTION edug_reject_web_filter_event_mutation()")
    op.drop_index("ix_device_web_filter_events_device_observed", table_name="device_web_filter_events")
    op.drop_table("device_web_filter_events")
    with op.batch_alter_table("administrator_permissions") as batch:
        batch.drop_constraint("ck_administrator_permissions_permission", type_="check")
        batch.create_check_constraint(
            "ck_administrator_permissions_permission",
            "permission IN ('administrator.manage','enrollment_token.issue',"
            "'enrollment_token.revoke','device_credential.revoke','policy.assign','device.control')",
        )
