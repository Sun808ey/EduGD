"""Add transactional forensic policy-assignment metadata.

Revision ID: c3f8a1d6e4b9
Revises: b7e1d4c9a2f6
Create Date: 2026-08-08 11:00:00.000000

"""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "c3f8a1d6e4b9"
down_revision = "b7e1d4c9a2f6"
branch_labels = None
depends_on = None

MIGRATION_SUBJECT = "migration:c3f8a1d6e4b9-policy-assignments"
MIGRATION_REASON = "Converted legacy policy assignment"
PERMISSIONS = (
    "'administrator.manage', 'enrollment_token.issue', "
    "'enrollment_token.revoke', 'device_credential.revoke', 'policy.assign'"
)
LEGACY_PERMISSIONS = (
    "'administrator.manage', 'enrollment_token.issue', "
    "'enrollment_token.revoke', 'device_credential.revoke'"
)


def upgrade() -> None:
    connection = op.get_bind()
    with op.batch_alter_table("administrator_permissions") as batch_op:
        batch_op.drop_constraint(
            "ck_administrator_permissions_permission",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_administrator_permissions_permission",
            f"permission IN ({PERMISSIONS})",
        )

    op.add_column(
        "device_policy_assignments",
        sa.Column("event_uuid", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "device_policy_assignments",
        sa.Column("assigned_by_administrator_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "device_policy_assignments",
        sa.Column("trusted_operator_subject", sa.String(255), nullable=True),
    )
    op.add_column(
        "device_policy_assignments",
        sa.Column("reason", sa.String(512), nullable=True),
    )

    assignment_table = sa.table(
        "device_policy_assignments",
        sa.column("id", sa.Integer()),
        sa.column("event_uuid", sa.Uuid()),
        sa.column("trusted_operator_subject", sa.String()),
        sa.column("reason", sa.String()),
    )
    assignment_ids = connection.execute(
        sa.select(assignment_table.c.id).order_by(assignment_table.c.id)
    ).scalars()
    for assignment_id in assignment_ids:
        connection.execute(
            assignment_table.update()
            .where(assignment_table.c.id == assignment_id)
            .values(
                event_uuid=uuid4(),
                trusted_operator_subject=MIGRATION_SUBJECT,
                reason=MIGRATION_REASON,
            )
        )

    incomplete = connection.scalar(
        sa.text(
            "SELECT count(*) FROM device_policy_assignments "
            "WHERE event_uuid IS NULL OR reason IS NULL OR "
            "trusted_operator_subject IS NULL"
        )
    )
    if incomplete:
        raise RuntimeError("policy assignment metadata conversion failed")

    with op.batch_alter_table("device_policy_assignments") as batch_op:
        batch_op.alter_column(
            "event_uuid",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        batch_op.alter_column(
            "reason",
            existing_type=sa.String(512),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_device_policy_assignments_event_uuid",
            ["event_uuid"],
        )
        batch_op.create_foreign_key(
            "fk_device_policy_assignments_assigned_by_administrator_id",
            "administrators",
            ["assigned_by_administrator_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "ck_device_policy_assignments_actor",
            "(assigned_by_administrator_id IS NOT NULL AND "
            "trusted_operator_subject IS NULL) OR "
            "(assigned_by_administrator_id IS NULL AND "
            "trusted_operator_subject IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_device_policy_assignments_reason_bounded",
            "length(reason) BETWEEN 1 AND 512",
        )
        batch_op.create_check_constraint(
            "ck_device_policy_assignments_operator_bounded",
            "trusted_operator_subject IS NULL OR "
            "length(trusted_operator_subject) BETWEEN 1 AND 255",
        )
    op.create_index(
        "ix_device_policy_assignments_assigned_by_administrator_id",
        "device_policy_assignments",
        ["assigned_by_administrator_id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
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
        {"subject": MIGRATION_SUBJECT, "reason": MIGRATION_REASON},
    )
    policy_permission_count = connection.scalar(
        sa.text(
            "SELECT count(*) FROM administrator_permissions "
            "WHERE permission = 'policy.assign'"
        )
    )
    if unsafe_policy_count or nonlegacy_assignments or policy_permission_count:
        raise RuntimeError(
            "policy assignment downgrade refused: forensic history would be lost"
        )

    op.drop_index(
        "ix_device_policy_assignments_assigned_by_administrator_id",
        table_name="device_policy_assignments",
    )
    with op.batch_alter_table("device_policy_assignments") as batch_op:
        batch_op.drop_constraint(
            "ck_device_policy_assignments_operator_bounded",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_device_policy_assignments_reason_bounded",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_device_policy_assignments_actor",
            type_="check",
        )
        batch_op.drop_constraint(
            "fk_device_policy_assignments_assigned_by_administrator_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "uq_device_policy_assignments_event_uuid",
            type_="unique",
        )
        batch_op.drop_column("reason")
        batch_op.drop_column("trusted_operator_subject")
        batch_op.drop_column("assigned_by_administrator_id")
        batch_op.drop_column("event_uuid")

    with op.batch_alter_table("administrator_permissions") as batch_op:
        batch_op.drop_constraint(
            "ck_administrator_permissions_permission",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_administrator_permissions_permission",
            f"permission IN ({LEGACY_PERMISSIONS})",
        )
