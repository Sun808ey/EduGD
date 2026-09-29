"""Store immutable, dual-approved physical device capability certifications.

Revision ID: d8f1a3c6e9b2
Revises: c7e5a9d2f4b8
"""

import sqlalchemy as sa
from alembic import op

revision = "d8f1a3c6e9b2"
down_revision = "c7e5a9d2f4b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_capability_certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("build_fingerprint", sa.String(512), nullable=False),
        sa.Column("record", sa.JSON(), nullable=False),
        sa.Column("record_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("previous_record_hash", sa.LargeBinary(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "record_hash", name="uq_device_capability_certifications_hash"
        ),
        sa.CheckConstraint(
            "length(record_hash) = 32", name="ck_device_capability_certifications_hash"
        ),
        sa.CheckConstraint(
            "previous_record_hash IS NULL OR length(previous_record_hash) = 32",
            name="ck_device_capability_certifications_previous_hash",
        ),
    )
    op.create_index(
        "ix_device_capability_certifications_fingerprint",
        "device_capability_certifications",
        ["build_fingerprint", "created_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE device_capability_certifications ENABLE ROW LEVEL SECURITY"
        )
        op.execute(
            "REVOKE ALL PRIVILEGES ON TABLE device_capability_certifications FROM PUBLIC"
        )
        op.execute(
            """DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL PRIVILEGES ON TABLE device_capability_certifications FROM anon; END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL PRIVILEGES ON TABLE device_capability_certifications FROM authenticated; END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN REVOKE ALL PRIVILEGES ON TABLE device_capability_certifications FROM service_role; END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN REVOKE ALL PRIVILEGES ON TABLE device_capability_certifications FROM edug_runtime; END IF;
            END $$"""
        )
        op.execute(
            """CREATE FUNCTION edug_reject_certification_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'certification evidence is immutable'; END;
            $$ LANGUAGE plpgsql"""
        )
        op.execute(
            "CREATE TRIGGER trg_device_capability_certifications_immutable "
            "BEFORE UPDATE OR DELETE ON device_capability_certifications "
            "FOR EACH ROW EXECUTE FUNCTION edug_reject_certification_mutation()"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER trg_device_capability_certifications_immutable ON device_capability_certifications"
        )
        op.execute("DROP FUNCTION edug_reject_certification_mutation()")
    op.drop_index(
        "ix_device_capability_certifications_fingerprint",
        table_name="device_capability_certifications",
    )
    op.drop_table("device_capability_certifications")
