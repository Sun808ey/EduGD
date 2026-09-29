"""Harden PostgreSQL function resolution and execution grants.

Revision ID: ab4e6f2c9d71
Revises: fa3d7e1b9c42
"""

from alembic import op

revision = "ab4e6f2c9d71"
down_revision = "fa3d7e1b9c42"
branch_labels = None
depends_on = None


_FUNCTIONS = (
    "edug_reject_certification_mutation()",
    "edug_reject_device_audit_mutation()",
    "edug_reject_device_status_evidence_mutation()",
    "edug_reject_policy_assignment_event_mutation()",
    "edug_reject_policy_revision_mutation()",
    "edug_reject_policy_sync_event_mutation()",
    "edug_reject_device_control_event_mutation()",
    "edug_valid_blocked_apps(value json)",
    "edug_valid_policy_revision_payload(value json)",
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # The v3 migration replaced this function. Recreate it with the same
    # validation semantics but an explicitly qualified application function.
    op.execute(
        """CREATE OR REPLACE FUNCTION public.edug_valid_policy_revision_payload(value json)
        RETURNS boolean LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
        SET search_path = '' AS $function$
            SELECT CASE
                WHEN json_typeof(value) <> 'object' THEN FALSE
                WHEN json_typeof(value->'schema_version') <> 'number' THEN FALSE
                WHEN (value->>'schema_version')::integer = 3 THEN TRUE
                WHEN (value->>'schema_version')::integer <> 1 THEN FALSE
                WHEN (SELECT count(*) FROM json_object_keys(value)) <> 2 THEN FALSE
                WHEN value->'blocked_apps' IS NULL THEN FALSE
                ELSE public.edug_valid_blocked_apps(value->'blocked_apps')
            END
        $function$"""
    )
    for function in _FUNCTIONS:
        op.execute(f"ALTER FUNCTION public.{function} SET search_path = ''")
        op.execute(f"REVOKE ALL ON FUNCTION public.{function} FROM PUBLIC")
        op.execute(
            f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL ON FUNCTION public.{function} FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL ON FUNCTION public.{function} FROM authenticated;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                REVOKE ALL ON FUNCTION public.{function} FROM service_role;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'edug_runtime') THEN
                GRANT EXECUTE ON FUNCTION public.{function} TO edug_runtime;
            END IF;
            END $$"""
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for function in _FUNCTIONS:
        op.execute(f"ALTER FUNCTION public.{function} RESET search_path")
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{function} TO PUBLIC")
