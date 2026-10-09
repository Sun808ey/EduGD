"""Create the single-school administrator registration record.

Revision ID: c8d2e7f4a1b6
Revises: b6e2f9a4c7d1
Create Date: 2026-10-05 16:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "c8d2e7f4a1b6"
down_revision = "b6e2f9a4c7d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_uuid", sa.Uuid(), nullable=False),
        sa.Column("singleton_key", sa.String(length=1), nullable=False, server_default="1"),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("district", sa.String(length=120), nullable=False),
        sa.Column("school_type", sa.String(length=80), nullable=False),
        sa.Column("contact_person", sa.String(length=120), nullable=False),
        sa.Column("official_telephone", sa.String(length=32), nullable=False),
        sa.Column("official_email", sa.String(length=254), nullable=True),
        sa.Column("physical_location", sa.String(length=255), nullable=False),
        sa.Column("authorised_administrator_name", sa.String(length=120), nullable=False),
        sa.Column("registered_by_administrator_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("singleton_key = '1'", name="ck_schools_singleton"),
        sa.CheckConstraint("length(name) BETWEEN 1 AND 160", name="ck_schools_name_bounded"),
        sa.CheckConstraint("length(district) BETWEEN 1 AND 120", name="ck_schools_district_bounded"),
        sa.CheckConstraint("length(school_type) BETWEEN 1 AND 80", name="ck_schools_type_bounded"),
        sa.CheckConstraint("length(contact_person) BETWEEN 1 AND 120", name="ck_schools_contact_bounded"),
        sa.CheckConstraint("length(official_telephone) BETWEEN 7 AND 32", name="ck_schools_phone_bounded"),
        sa.CheckConstraint("official_email IS NULL OR length(official_email) BETWEEN 3 AND 254", name="ck_schools_email_bounded"),
        sa.CheckConstraint("length(physical_location) BETWEEN 1 AND 255", name="ck_schools_location_bounded"),
        sa.CheckConstraint("length(authorised_administrator_name) BETWEEN 1 AND 120", name="ck_schools_administrator_bounded"),
        sa.ForeignKeyConstraint(["registered_by_administrator_id"], ["administrators.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("school_uuid", name="uq_schools_uuid"),
        sa.UniqueConstraint("singleton_key", name="uq_schools_singleton"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE schools ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE schools FROM PUBLIC")
        op.execute(
            """DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                GRANT SELECT, INSERT ON schools TO edug_runtime;
                GRANT USAGE, SELECT ON SEQUENCE schools_id_seq TO edug_runtime;
                EXECUTE 'CREATE POLICY edug_backend_runtime ON schools FOR ALL '
                    'TO edug_runtime USING (true) WITH CHECK (true)';
            END IF;
            END $$"""
        )


def downgrade() -> None:
    op.drop_table("schools")
