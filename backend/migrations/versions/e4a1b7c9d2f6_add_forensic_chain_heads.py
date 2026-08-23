"""Add immutable assignment events and forensic chain heads.

Revision ID: e4a1b7c9d2f6
Revises: d9b4e7a2c6f1
Create Date: 2026-08-10 12:00:00.000000
"""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "e4a1b7c9d2f6"
down_revision = "d9b4e7a2c6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_policy_synchronization_events_hash",
        "policy_synchronization_events",
        ["event_hash"],
        unique=True,
    )
    op.create_table(
        "policy_assignment_chain_heads",
        sa.Column("device_id", sa.Integer(), primary_key=True),
        sa.Column("head_event_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("length(head_event_hash) = 32", name="ck_policy_assignment_chain_heads_hash_length"),
    )
    op.create_table(
        "policy_assignment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("previous_assignment_id", sa.Integer(), nullable=True),
        sa.Column("administrator_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("previous_event_hash", sa.LargeBinary(32), nullable=True),
        sa.Column("event_hash", sa.LargeBinary(32), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assignment_id"], ["device_policy_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_assignment_id"], ["device_policy_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["administrator_id"], ["administrators.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_uuid", name="uq_policy_assignment_events_uuid"),
        sa.UniqueConstraint("event_hash", name="uq_policy_assignment_events_hash"),
        sa.CheckConstraint("operation IN ('assign', 'replace', 'clear')", name="ck_policy_assignment_events_operation"),
        sa.CheckConstraint("length(reason) BETWEEN 1 AND 512", name="ck_policy_assignment_events_reason_bounded"),
        sa.CheckConstraint("previous_event_hash IS NULL OR length(previous_event_hash) = 32", name="ck_policy_assignment_events_previous_hash_length"),
        sa.CheckConstraint("length(event_hash) = 32", name="ck_policy_assignment_events_hash_length"),
    )
    op.create_index("ix_policy_assignment_events_device_created", "policy_assignment_events", ["device_id", "created_at"])
    op.create_table(
        "policy_synchronization_chain_heads",
        sa.Column("requested_device_pseudonym", sa.LargeBinary(32), primary_key=True),
        sa.Column("head_event_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(requested_device_pseudonym) = 32", name="ck_policy_sync_chain_heads_pseudonym_length"),
        sa.CheckConstraint("length(head_event_hash) = 32", name="ck_policy_sync_chain_heads_hash_length"),
    )
    _backfill_assignment_events()
    _backfill_sync_heads()
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION edug_reject_policy_assignment_event_mutation()
            RETURNS trigger AS $$ BEGIN
                RAISE EXCEPTION 'policy assignment events are immutable';
            END; $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER trg_policy_assignment_events_immutable
            BEFORE UPDATE OR DELETE ON policy_assignment_events
            FOR EACH ROW EXECUTE FUNCTION edug_reject_policy_assignment_event_mutation()
        """)


def _backfill_assignment_events() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT assignment.id, assignment.device_id, assignment.assigned_by_administrator_id, "
        "assignment.reason, assignment.assigned_at FROM device_policy_assignments AS assignment "
        "WHERE assignment.assigned_by_administrator_id IS NOT NULL "
        "ORDER BY assignment.device_id, assignment.assigned_at, assignment.id"
    )).mappings()
    heads: dict[int, bytes] = {}
    for row in rows:
        event_uuid = uuid4()
        created_at = row["assigned_at"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        previous = heads.get(row["device_id"])
        evidence = {
            "administrator_id": row["assigned_by_administrator_id"],
            "assignment_id": row["id"],
            "created_at": created_at.isoformat(),
            "device_id": row["device_id"],
            "event_uuid": str(event_uuid),
            "operation": "assign",
            "previous_assignment_id": None,
            "previous_event_hash": previous.hex() if previous else None,
            "reason": row["reason"],
        }
        event_hash = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).digest()
        connection.execute(sa.text(
            "INSERT INTO policy_assignment_events "
            "(event_uuid, device_id, assignment_id, previous_assignment_id, administrator_id, operation, reason, created_at, previous_event_hash, event_hash) "
            "VALUES (:event_uuid, :device_id, :assignment_id, NULL, :administrator_id, 'assign', :reason, :created_at, :previous_event_hash, :event_hash)"
        ), {**row, "event_uuid": event_uuid, "previous_event_hash": previous, "event_hash": event_hash, "created_at": created_at})
        heads[row["device_id"]] = event_hash
    for device_id, head in heads.items():
        connection.execute(sa.text(
            "INSERT INTO policy_assignment_chain_heads (device_id, head_event_hash) VALUES (:device_id, :head)"
        ), {"device_id": device_id, "head": head})


def _backfill_sync_heads() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT requested_device_pseudonym, event_hash FROM policy_synchronization_events "
        "ORDER BY requested_device_pseudonym, requested_at, id"
    )).mappings()
    heads: dict[bytes, bytes] = {}
    for row in rows:
        heads[row["requested_device_pseudonym"]] = row["event_hash"]
    for pseudonym, head in heads.items():
        connection.execute(sa.text(
            "INSERT INTO policy_synchronization_chain_heads (requested_device_pseudonym, head_event_hash) VALUES (:pseudonym, :head)"
        ), {"pseudonym": pseudonym, "head": head})


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM policy_assignment_events")):
        raise RuntimeError("forensic chain downgrade refused: assignment evidence would be lost")
    if connection.dialect.name == "postgresql":
        op.execute("DROP TRIGGER trg_policy_assignment_events_immutable ON policy_assignment_events")
        op.execute("DROP FUNCTION edug_reject_policy_assignment_event_mutation()")
    op.drop_table("policy_synchronization_chain_heads")
    op.drop_index(
        "uq_policy_synchronization_events_hash",
        table_name="policy_synchronization_events",
    )
    op.drop_index("ix_policy_assignment_events_device_created", table_name="policy_assignment_events")
    op.drop_table("policy_assignment_events")
    op.drop_table("policy_assignment_chain_heads")
