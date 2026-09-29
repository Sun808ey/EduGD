"""Add DPC v3 device-control state and evidence.

Revision ID: fa3d7e1b9c42
Revises: d8f1a3c6e9b2
"""
import sqlalchemy as sa
from alembic import op

revision = "fa3d7e1b9c42"
down_revision = "d8f1a3c6e9b2"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        # v3 payload semantics are enforced by the application contract before
        # persistence. Keep the database constraint strict for legacy v1 rows
        # while allowing the additive v3 schema.
        op.execute(
            """CREATE OR REPLACE FUNCTION edug_valid_policy_revision_payload(value json)
            RETURNS boolean LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $function$
                SELECT CASE
                    WHEN json_typeof(value) <> 'object' THEN FALSE
                    WHEN json_typeof(value->'schema_version') <> 'number' THEN FALSE
                    WHEN (value->>'schema_version')::integer = 3 THEN TRUE
                    WHEN (value->>'schema_version')::integer <> 1 THEN FALSE
                    WHEN (SELECT count(*) FROM json_object_keys(value)) <> 2 THEN FALSE
                    WHEN value->'blocked_apps' IS NULL THEN FALSE
                    ELSE edug_valid_blocked_apps(value->'blocked_apps')
                END
            $function$"""
        )
    with op.batch_alter_table("administrator_permissions") as batch:
        batch.drop_constraint("ck_administrator_permissions_permission", type_="check")
        batch.create_check_constraint("ck_administrator_permissions_permission", "permission IN ('administrator.manage','enrollment_token.issue','enrollment_token.revoke','device_credential.revoke','policy.assign','device.control')")
    op.create_table("device_block_overrides", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("reason", sa.String(512), nullable=False), sa.Column("issued_by_administrator_id", sa.Integer(), nullable=False), sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("cleared_by_administrator_id", sa.Integer()), sa.Column("cleared_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["issued_by_administrator_id"], ["administrators.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["cleared_by_administrator_id"], ["administrators.id"], ondelete="RESTRICT"), sa.UniqueConstraint("device_id"), sa.UniqueConstraint("device_id", "version", name="uq_device_block_overrides_version"), sa.CheckConstraint("version >= 1", name="ck_device_block_overrides_version"), sa.CheckConstraint("status IN ('active', 'cleared')", name="ck_device_block_overrides_status"))
    op.create_table("device_control_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), nullable=False), sa.Column("override_id", sa.Integer(), nullable=False), sa.Column("administrator_id", sa.Integer(), nullable=False), sa.Column("operation", sa.String(16), nullable=False), sa.Column("reason", sa.String(512), nullable=False), sa.Column("content_hash", sa.LargeBinary(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["override_id"], ["device_block_overrides.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["administrator_id"], ["administrators.id"], ondelete="RESTRICT"), sa.CheckConstraint("operation IN ('block', 'clear')", name="ck_device_control_events_operation"), sa.CheckConstraint("length(content_hash) = 32", name="ck_device_control_events_hash"))
    op.create_index("ix_device_control_events_device_created", "device_control_events", ["device_id", "created_at"])
    op.create_table("device_usage_daily", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), nullable=False), sa.Column("usage_date", sa.Date(), nullable=False), sa.Column("active_minutes", sa.Integer(), nullable=False), sa.Column("policy_uuid", sa.Uuid(), nullable=False), sa.Column("revision_uuid", sa.Uuid(), nullable=False), sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"), sa.UniqueConstraint("device_id", "usage_date", name="uq_device_usage_daily_date"), sa.CheckConstraint("active_minutes BETWEEN 0 AND 1440", name="ck_device_usage_daily_minutes"))
    if op.get_bind().dialect.name == "postgresql":
        for table in ("device_block_overrides", "device_control_events", "device_usage_daily"):
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
            if table == "device_block_overrides":
                privileges = "SELECT, INSERT, UPDATE"
            elif table == "device_usage_daily":
                privileges = "SELECT, INSERT, UPDATE"
            else:
                privileges = "SELECT, INSERT"
            op.execute(
                f"""DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                    GRANT {privileges} ON TABLE {table} TO edug_runtime;
                END IF;
                END $$"""
            )
            op.execute(
                f"""DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                    CREATE POLICY edug_backend_runtime ON {table}
                    AS PERMISSIVE FOR ALL TO edug_runtime USING (true) WITH CHECK (true);
                END IF;
                END $$"""
            )
        op.execute(
            """DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO edug_runtime;
            END IF;
            END $$"""
        )
        op.execute("""CREATE FUNCTION edug_reject_device_control_event_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'device control evidence is immutable'; END; $$ LANGUAGE plpgsql""")
        op.execute("CREATE TRIGGER trg_device_control_events_immutable BEFORE UPDATE OR DELETE ON device_control_events FOR EACH ROW EXECUTE FUNCTION edug_reject_device_control_event_mutation()")

def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER trg_device_control_events_immutable ON device_control_events")
        op.execute("DROP FUNCTION edug_reject_device_control_event_mutation()")
    with op.batch_alter_table("administrator_permissions") as batch:
        batch.drop_constraint("ck_administrator_permissions_permission", type_="check")
        batch.create_check_constraint("ck_administrator_permissions_permission", "permission IN ('administrator.manage','enrollment_token.issue','enrollment_token.revoke','device_credential.revoke','policy.assign')")
    op.drop_table("device_usage_daily")
    op.drop_index("ix_device_control_events_device_created", table_name="device_control_events")
    op.drop_table("device_control_events")
    op.drop_table("device_block_overrides")
