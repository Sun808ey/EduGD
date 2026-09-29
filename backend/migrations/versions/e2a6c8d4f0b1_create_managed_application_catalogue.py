"""Create the managed application catalogue.

Revision ID: e2a6c8d4f0b1
Revises: d1f7b3c9e5a2
"""

import sqlalchemy as sa
from alembic import op

revision = "e2a6c8d4f0b1"
down_revision = "d1f7b3c9e5a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managed_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_uuid", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("package_name", sa.String(255), nullable=False),
        sa.Column("signing_certificate_sha256", sa.LargeBinary(32), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("education_approved", sa.Boolean(), nullable=False),
        sa.Column("mandatory_block", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(16), server_default="enabled", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("application_uuid", name="uq_managed_applications_uuid"),
        sa.UniqueConstraint("package_name", name="uq_managed_applications_package"),
        sa.CheckConstraint("status IN ('enabled', 'disabled')", name="ck_managed_applications_status"),
        sa.CheckConstraint("length(display_name) BETWEEN 1 AND 120", name="ck_managed_applications_display_name"),
        sa.CheckConstraint("category = lower(category) AND length(category) BETWEEN 1 AND 64", name="ck_managed_applications_category"),
        sa.CheckConstraint("signing_certificate_sha256 IS NULL OR length(signing_certificate_sha256) = 32", name="ck_managed_applications_signing_digest"),
    )
    op.create_index(
        "ix_managed_applications_status_category",
        "managed_applications",
        ["status", "category"],
    )
    if op.get_bind().dialect.name == "postgresql":
        # The catalogue is reachable only through the backend runtime role.
        # Keep it inaccessible through Supabase's exposed public schema.
        op.execute("ALTER TABLE managed_applications ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE managed_applications FROM PUBLIC")
        op.execute(
            """DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_applications FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_applications FROM authenticated;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_applications FROM service_role;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_applications FROM edug_runtime;
                GRANT SELECT, INSERT, UPDATE ON TABLE managed_applications TO edug_runtime;
                CREATE POLICY edug_backend_runtime ON managed_applications
                AS PERMISSIVE FOR ALL TO edug_runtime USING (true) WITH CHECK (true);
                GRANT USAGE, SELECT ON SEQUENCE managed_applications_id_seq TO edug_runtime;
            END IF;
            END $$"""
        )


def downgrade() -> None:
    op.drop_index("ix_managed_applications_status_category", table_name="managed_applications")
    op.drop_table("managed_applications")
