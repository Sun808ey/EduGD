"""Add append-only policy synchronization audit events.

Revision ID: d9b4e7a2c6f1
Revises: c3f8a1d6e4b9
Create Date: 2026-08-08 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "d9b4e7a2c6f1"
down_revision = "c3f8a1d6e4b9"
branch_labels = None
depends_on = None
LEGACY_ASSIGNMENT_SUBJECT = "migration:c3f8a1d6e4b9-policy-assignments"
LEGACY_ASSIGNMENT_REASON = "Converted legacy policy assignment"


def upgrade() -> None:
    op.create_table(
        "policy_synchronization_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_uuid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("requested_device_pseudonym", sa.LargeBinary(32), nullable=False),
        sa.Column("reported_client_version", sa.Integer(), nullable=True),
        sa.Column("reported_policy_uuid", sa.Uuid(), nullable=True),
        sa.Column("reported_revision_uuid", sa.Uuid(), nullable=True),
        sa.Column("server_policy_version", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("outcome_category", sa.String(64), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("previous_event_hash", sa.LargeBinary(32), nullable=True),
        sa.Column("event_hash", sa.LargeBinary(32), nullable=False),
        sa.UniqueConstraint(
            "event_uuid", name="uq_policy_synchronization_events_uuid"
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"], ["device_credentials.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "operation IN ('apply', 'no_change', 'clear', 'rollback', "
            "'blocked', 'error')",
            name="ck_policy_synchronization_events_operation",
        ),
        sa.CheckConstraint(
            "outcome_category IN ('success', 'no_assignment', "
            "'device_not_found', 'device_inactive', 'policy_inactive', "
            "'policy_revoked', 'assignment_corruption', "
            "'revision_mismatch', 'internal_error', 'invalid_request')",
            name="ck_policy_synchronization_events_outcome",
        ),
        sa.CheckConstraint(
            "reported_client_version IS NULL OR reported_client_version "
            "BETWEEN 0 AND 2147483647",
            name="ck_policy_synchronization_events_client_version",
        ),
        sa.CheckConstraint(
            "server_policy_version IS NULL OR server_policy_version >= 0",
            name="ck_policy_synchronization_events_server_version",
        ),
        sa.CheckConstraint(
            "length(requested_device_pseudonym) = 32",
            name="ck_policy_synchronization_events_device_pseudonym_length",
        ),
        sa.CheckConstraint(
            "previous_event_hash IS NULL OR length(previous_event_hash) = 32",
            name="ck_policy_synchronization_events_previous_hash_length",
        ),
        sa.CheckConstraint(
            "length(event_hash) = 32",
            name="ck_policy_synchronization_events_hash_length",
        ),
    )
    op.create_index(
        "ix_policy_synchronization_events_device_requested",
        "policy_synchronization_events",
        ["device_id", "requested_at"],
    )
    op.create_index(
        "ix_policy_synchronization_events_pseudonym_requested",
        "policy_synchronization_events",
        ["requested_device_pseudonym", "requested_at"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION edug_reject_policy_sync_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'policy synchronization events are immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_policy_synchronization_events_immutable
            BEFORE UPDATE OR DELETE ON policy_synchronization_events
            FOR EACH ROW EXECUTE FUNCTION edug_reject_policy_sync_event_mutation()
            """
        )


def downgrade() -> None:
    connection = op.get_bind()
    event_count = connection.scalar(
        sa.text("SELECT count(*) FROM policy_synchronization_events")
    )
    unsafe_policy_count = connection.scalar(
        sa.text(
            "SELECT count(*) FROM ("
            "SELECT policy.id FROM policies AS policy "
            "LEFT JOIN policy_revisions AS revision "
            "ON revision.policy_id = policy.id "
            "GROUP BY policy.id HAVING count(revision.id) <> 1"
            ") AS unsafe_policies"
        )
    )
    nonlegacy_assignments = connection.scalar(
        sa.text(
            "SELECT count(*) FROM device_policy_assignments "
            "WHERE assigned_by_administrator_id IS NOT NULL OR "
            "trusted_operator_subject <> :subject OR reason <> :reason"
        ),
        {
            "subject": LEGACY_ASSIGNMENT_SUBJECT,
            "reason": LEGACY_ASSIGNMENT_REASON,
        },
    )
    policy_permission_count = connection.scalar(
        sa.text(
            "SELECT count(*) FROM administrator_permissions "
            "WHERE permission = 'policy.assign'"
        )
    )
    if (
        event_count
        or unsafe_policy_count
        or nonlegacy_assignments
        or policy_permission_count
    ):
        raise RuntimeError(
            "synchronization audit downgrade refused: forensic history "
            "would be lost"
        )

    if connection.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER trg_policy_synchronization_events_immutable "
            "ON policy_synchronization_events"
        )
        op.execute("DROP FUNCTION edug_reject_policy_sync_event_mutation()")
    op.drop_index(
        "ix_policy_synchronization_events_pseudonym_requested",
        table_name="policy_synchronization_events",
    )
    op.drop_index(
        "ix_policy_synchronization_events_device_requested",
        table_name="policy_synchronization_events",
    )
    op.drop_table("policy_synchronization_events")
