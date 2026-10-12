"""Create the managed domain catalogue.

Revision ID: h2c3d4e5f6a7
Revises: g1b2c3d4e5f6
"""

import sqlalchemy as sa
from alembic import op
from uuid import UUID

revision = "h2c3d4e5f6a7"
down_revision = "g1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managed_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain_uuid", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), server_default="enabled", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("domain_uuid", name="uq_managed_domains_uuid"),
        sa.UniqueConstraint("domain", name="uq_managed_domains_domain"),
        sa.CheckConstraint("status IN ('enabled', 'disabled')", name="ck_managed_domains_status"),
        sa.CheckConstraint("category = lower(category) AND length(category) BETWEEN 1 AND 64", name="ck_managed_domains_category"),
    )
    op.create_index("ix_managed_domains_status_category", "managed_domains", ["status", "category"])
    domains = sa.table(
        "managed_domains",
        sa.column("domain_uuid", sa.Uuid()),
        sa.column("domain", sa.String()),
        sa.column("category", sa.String()),
        sa.column("status", sa.String()),
    )
    op.bulk_insert(
        domains,
        [
            {"domain_uuid": UUID("11111111-1111-4111-8111-111111111111"), "domain": "facebook.com", "category": "social", "status": "enabled"},
            {"domain_uuid": UUID("22222222-2222-4222-8222-222222222222"), "domain": "instagram.com", "category": "social", "status": "enabled"},
            {"domain_uuid": UUID("33333333-3333-4333-8333-333333333333"), "domain": "tiktok.com", "category": "social", "status": "enabled"},
            {"domain_uuid": UUID("44444444-4444-4444-8444-444444444444"), "domain": "youtube.com", "category": "video", "status": "enabled"},
            {"domain_uuid": UUID("55555555-5555-4555-8555-555555555555"), "domain": "roblox.com", "category": "games", "status": "enabled"},
            {"domain_uuid": UUID("66666666-6666-4666-8666-666666666666"), "domain": "minecraft.net", "category": "games", "status": "enabled"},
        ],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE managed_domains ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE managed_domains FROM PUBLIC")
        op.execute(
            """DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_domains FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_domains FROM authenticated;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_domains FROM service_role;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                REVOKE ALL PRIVILEGES ON TABLE managed_domains FROM edug_runtime;
                GRANT SELECT, INSERT, UPDATE ON TABLE managed_domains TO edug_runtime;
                CREATE POLICY edug_backend_runtime ON managed_domains
                AS PERMISSIVE FOR ALL TO edug_runtime USING (true) WITH CHECK (true);
                GRANT USAGE, SELECT ON SEQUENCE managed_domains_id_seq TO edug_runtime;
            END IF;
            END $$"""
        )


def downgrade() -> None:
    op.drop_index("ix_managed_domains_status_category", table_name="managed_domains")
    op.drop_table("managed_domains")
