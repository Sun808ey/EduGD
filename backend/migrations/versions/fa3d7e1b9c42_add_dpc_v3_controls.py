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
