"""Create the persistent Sunbird translation cache.

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
"""

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "translation_cache_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_language", sa.String(8), nullable=False),
        sa.Column("target_language", sa.String(3), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source_text", sa.String(4000), nullable=False),
        sa.Column("translated_text", sa.String(4000), nullable=False),
        sa.Column("provider", sa.String(32), server_default="sunbird", nullable=False),
        sa.Column("quality_status", sa.String(16), server_default="machine", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "source_language",
            "target_language",
            "source_hash",
            name="uq_translation_cache_identity",
        ),
        sa.CheckConstraint("provider = 'sunbird'", name="ck_translation_cache_provider"),
        sa.CheckConstraint(
            "quality_status IN ('machine', 'reviewed', 'approved')",
            name="ck_translation_cache_quality_status",
        ),
    )
    op.create_index(
        "ix_translation_cache_lookup",
        "translation_cache_entries",
        ["source_language", "target_language", "source_hash"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE translation_cache_entries ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE translation_cache_entries FROM PUBLIC")
        op.execute(
            """DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL PRIVILEGES ON TABLE translation_cache_entries FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL PRIVILEGES ON TABLE translation_cache_entries FROM authenticated;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                REVOKE ALL PRIVILEGES ON TABLE translation_cache_entries FROM service_role;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                REVOKE ALL PRIVILEGES ON TABLE translation_cache_entries FROM edug_runtime;
                GRANT SELECT, INSERT, UPDATE ON TABLE translation_cache_entries TO edug_runtime;
                GRANT USAGE, SELECT ON SEQUENCE translation_cache_entries_id_seq TO edug_runtime;
                CREATE POLICY edug_backend_runtime ON translation_cache_entries
                AS PERMISSIVE FOR ALL TO edug_runtime USING (true) WITH CHECK (true);
            END IF;
            END $$"""
        )


def downgrade() -> None:
    op.drop_index("ix_translation_cache_lookup", table_name="translation_cache_entries")
    op.drop_table("translation_cache_entries")
