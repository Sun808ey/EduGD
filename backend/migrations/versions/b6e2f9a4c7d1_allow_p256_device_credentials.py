"""Allow the canonical P-256 DPC credential algorithm.

Revision ID: b6e2f9a4c7d1
Revises: a7b8c9d0e1f2
"""

from alembic import op

revision = "b6e2f9a4c7d1"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("device_credentials") as batch_op:
        batch_op.drop_constraint("ck_device_credentials_algorithm", type_="check")
        batch_op.create_check_constraint(
            "ck_device_credentials_algorithm",
            "algorithm IN ('ECDSA_P256_SHA256', 'RSA_2048_SHA256')",
        )


def downgrade() -> None:
    with op.batch_alter_table("device_credentials") as batch_op:
        batch_op.drop_constraint("ck_device_credentials_algorithm", type_="check")
        batch_op.create_check_constraint(
            "ck_device_credentials_algorithm",
            "algorithm IN ('RSA_2048_SHA256')",
        )
