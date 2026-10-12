"""Grant the runtime role access to tables added after the base schema.

Revision ID: i4e5f6a7b8c9
Revises: h2c3d4e5f6a7
"""

from alembic import op

revision = "i4e5f6a7b8c9"
down_revision = "h2c3d4e5f6a7"
branch_labels = None
depends_on = None


RUNTIME_TABLES = (
    ("device_asset_change_events", "SELECT, INSERT, UPDATE"),
    ("device_location_assignments", "SELECT, INSERT, UPDATE"),
    ("incidents", "SELECT"),
)


def _runtime_policy_sql(table: str, privileges: str) -> str:
    sequence = f"{table}_id_seq"
    return f"""\
ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM service_role;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM edug_runtime;
        GRANT {privileges} ON TABLE public.{table} TO edug_runtime;
        DROP POLICY IF EXISTS edug_backend_runtime ON public.{table};
        CREATE POLICY edug_backend_runtime ON public.{table}
            AS PERMISSIVE FOR ALL TO edug_runtime
            USING (true) WITH CHECK (true);
        {f"GRANT USAGE, SELECT ON SEQUENCE public.{sequence} TO edug_runtime;" if table != "incidents" else ""}
    END IF;
END
$$;
"""


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table, privileges in RUNTIME_TABLES:
            op.execute(_runtime_policy_sql(table, privileges))


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table, _ in RUNTIME_TABLES:
            sequence = f"{table}_id_seq"
            op.execute(
                f"""\
DROP POLICY IF EXISTS edug_backend_runtime ON public.{table};
REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM edug_runtime;
{f"REVOKE ALL PRIVILEGES ON SEQUENCE public.{sequence} FROM edug_runtime;" if table != "incidents" else ""}
ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;
"""
            )
