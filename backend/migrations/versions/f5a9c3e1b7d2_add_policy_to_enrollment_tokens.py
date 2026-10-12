"""Attach policy revisions to enrollment tokens.

Revision ID: f5a9c3e1b7d2
Revises: d4e8a1c7b2f9
Create Date: 2026-10-05 18:15:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "f5a9c3e1b7d2"
down_revision = "d4e8a1c7b2f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("enrollment_tokens") as batch:
        batch.add_column(sa.Column("policy_revision_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_enrollment_tokens_policy_revision",
            "policy_revisions",
            ["policy_revision_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index(
            "ix_enrollment_tokens_policy_revision", ["policy_revision_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("enrollment_tokens") as batch:
        batch.drop_index("ix_enrollment_tokens_policy_revision")
        batch.drop_constraint(
            "fk_enrollment_tokens_policy_revision", type_="foreignkey"
        )
        batch.drop_column("policy_revision_id")
