"""Verify policy revision administrator provenance.

Revision ID: b7e1d4c9a2f6
Revises: a8d5e2f7c1b4
Create Date: 2026-08-08 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "b7e1d4c9a2f6"
down_revision = "a8d5e2f7c1b4"
branch_labels = None
depends_on = None

TRIGGER = "trg_policy_revisions_immutable"


def upgrade() -> None:
    connection = op.get_bind()
    is_postgresql = connection.dialect.name == "postgresql"
    actor_match = (
        "administrator.administrator_uuid::text = revision.created_by"
        if is_postgresql
        else "administrator.administrator_uuid = "
        "replace(revision.created_by, '-', '')"
    )
    unverified = connection.scalar(
        sa.text(
            "SELECT count(*) FROM policy_revisions AS revision "
            "WHERE revision.created_by NOT LIKE 'migration:%' "
            "AND NOT EXISTS (SELECT 1 FROM administrators AS administrator "
            f"WHERE {actor_match})"
        )
    )
    if unverified:
        raise RuntimeError(
            "policy revision actor migration refused: "
            "unverified administrator provenance"
        )

    op.add_column(
        "policy_revisions",
        sa.Column("created_by_administrator_id", sa.Integer(), nullable=True),
    )
    if is_postgresql:
        op.execute(f"DROP TRIGGER {TRIGGER} ON policy_revisions")
        op.execute(
            "UPDATE policy_revisions AS revision "
            "SET created_by_administrator_id = administrator.id "
            "FROM administrators AS administrator "
            "WHERE administrator.administrator_uuid::text = revision.created_by"
        )
        op.create_foreign_key(
            "fk_policy_revisions_created_by_administrator_id",
            "policy_revisions",
            "administrators",
            ["created_by_administrator_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_check_constraint(
            "ck_policy_revisions_actor_provenance",
            "policy_revisions",
            "(created_by_administrator_id IS NULL AND "
            "created_by LIKE 'migration:%') OR "
            "(created_by_administrator_id IS NOT NULL AND "
            "created_by NOT LIKE 'migration:%')",
        )
        op.execute(
            f"CREATE TRIGGER {TRIGGER} "
            "BEFORE UPDATE OR DELETE ON policy_revisions "
            "FOR EACH ROW EXECUTE FUNCTION "
            "edug_reject_policy_revision_mutation()"
        )
    else:
        connection.execute(
            sa.text(
                "UPDATE policy_revisions AS revision "
                "SET created_by_administrator_id = ("
                "SELECT administrator.id FROM administrators AS administrator "
                "WHERE administrator.administrator_uuid = "
                "replace(revision.created_by, '-', '')) "
                "WHERE revision.created_by NOT LIKE 'migration:%'"
            )
        )
    op.create_index(
        "ix_policy_revisions_created_by_administrator_id",
        "policy_revisions",
        ["created_by_administrator_id"],
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
    if unsafe_policy_count:
        raise RuntimeError(
            "immutable policy revision downgrade refused: "
            "every policy must have exactly one revision"
        )
    is_postgresql = connection.dialect.name == "postgresql"
    if is_postgresql:
        op.execute(f"DROP TRIGGER {TRIGGER} ON policy_revisions")
    op.drop_index(
        "ix_policy_revisions_created_by_administrator_id",
        table_name="policy_revisions",
    )
    if is_postgresql:
        op.drop_constraint(
            "ck_policy_revisions_actor_provenance",
            "policy_revisions",
            type_="check",
        )
        op.drop_constraint(
            "fk_policy_revisions_created_by_administrator_id",
            "policy_revisions",
            type_="foreignkey",
        )
    op.drop_column("policy_revisions", "created_by_administrator_id")
    if is_postgresql:
        op.execute(
            f"CREATE TRIGGER {TRIGGER} "
            "BEFORE UPDATE OR DELETE ON policy_revisions "
            "FOR EACH ROW EXECUTE FUNCTION "
            "edug_reject_policy_revision_mutation()"
        )
