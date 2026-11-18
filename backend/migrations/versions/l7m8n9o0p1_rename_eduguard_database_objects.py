"""Rename legacy application-owned PostgreSQL objects to EduGuard names.

Revision ID: l7m8n9o0p1
Revises: k6l7m8n9o0
"""

from alembic import op

revision = "l7m8n9o0p1"
down_revision = "k6l7m8n9o0"
branch_labels = None
depends_on = None


_FUNCTIONS = (
    ("edug_reject_certification_mutation", "eduguard_reject_certification_mutation", ""),
    ("edug_reject_device_audit_mutation", "eduguard_reject_device_audit_mutation", ""),
    (
        "edug_reject_device_status_evidence_mutation",
        "eduguard_reject_device_status_evidence_mutation",
        "",
    ),
    (
        "edug_reject_policy_assignment_event_mutation",
        "eduguard_reject_policy_assignment_event_mutation",
        "",
    ),
    ("edug_reject_policy_revision_mutation", "eduguard_reject_policy_revision_mutation", ""),
    ("edug_reject_policy_sync_event_mutation", "eduguard_reject_policy_sync_event_mutation", ""),
    ("edug_reject_device_control_event_mutation", "eduguard_reject_device_control_event_mutation", ""),
    ("edug_reject_web_filter_event_mutation", "eduguard_reject_web_filter_event_mutation", ""),
    ("edug_valid_blocked_apps", "eduguard_valid_blocked_apps", "json"),
    (
        "edug_valid_policy_revision_payload",
        "eduguard_valid_policy_revision_payload",
        "json",
    ),
)


def _rename_objects(old_prefix: str, new_prefix: str) -> None:
    op.execute(
        f"""DO $migration$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{old_prefix}_runtime')
               AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{new_prefix}_runtime') THEN
                RAISE EXCEPTION 'both {old_prefix}_runtime and {new_prefix}_runtime roles exist';
            ELSIF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{old_prefix}_runtime') THEN
                ALTER ROLE {old_prefix}_runtime RENAME TO {new_prefix}_runtime;
            END IF;
        END
        $migration$"""
    )

    functions = (
        _FUNCTIONS
        if old_prefix == "edug"
        else tuple((new, old, args) for old, new, args in _FUNCTIONS)
    )
    for old_name, new_name, argument_types in functions:
        old_signature = f"public.{old_name}({argument_types})"
        new_signature = f"public.{new_name}({argument_types})"
        op.execute(
            f"""DO $migration$
            BEGIN
                IF to_regprocedure('{old_signature}') IS NOT NULL
                   AND to_regprocedure('{new_signature}') IS NOT NULL THEN
                    RAISE EXCEPTION 'both {old_signature} and {new_signature} functions exist';
                ELSIF to_regprocedure('{old_signature}') IS NOT NULL THEN
                    EXECUTE 'ALTER FUNCTION {old_signature} RENAME TO {new_name}';
                END IF;
            END
            $migration$"""
        )

    op.execute(
        f"""DO $migration$
        DECLARE policy_record record;
        BEGIN
            FOR policy_record IN
                SELECT schemaname, tablename
                FROM pg_policies
                WHERE policyname = '{old_prefix}_backend_runtime'
            LOOP
                IF EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = policy_record.schemaname
                      AND tablename = policy_record.tablename
                      AND policyname = '{new_prefix}_backend_runtime'
                ) THEN
                    RAISE EXCEPTION 'both {old_prefix}_backend_runtime and {new_prefix}_backend_runtime policies exist on %.%',
                        policy_record.schemaname, policy_record.tablename;
                END IF;
                EXECUTE format(
                    'ALTER POLICY %I ON %I.%I RENAME TO %I',
                    '{old_prefix}_backend_runtime', policy_record.schemaname,
                    policy_record.tablename, '{new_prefix}_backend_runtime'
                );
            END LOOP;
        END
        $migration$"""
    )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    _rename_objects("edug", "eduguard")

    # The SQL-language validator body stores the helper's name as text, so
    # refresh it after renaming both functions.
    op.execute(
        """CREATE OR REPLACE FUNCTION public.eduguard_valid_policy_revision_payload(value json)
        RETURNS boolean LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
        SET search_path = '' AS $function$
            SELECT CASE
                WHEN json_typeof(value) <> 'object' THEN FALSE
                WHEN json_typeof(value->'schema_version') <> 'number' THEN FALSE
                WHEN (value->>'schema_version')::integer = 3 THEN TRUE
                WHEN (value->>'schema_version')::integer <> 1 THEN FALSE
                WHEN (SELECT count(*) FROM json_object_keys(value)) <> 2 THEN FALSE
                WHEN value->'blocked_apps' IS NULL THEN FALSE
                ELSE public.eduguard_valid_blocked_apps(value->'blocked_apps')
            END
        $function$"""
    )


def downgrade() -> None:
    # The migration history itself now uses the EduGuard object names. Keep
    # those canonical names while rolling back schema revisions so their
    # downgrade functions can still find and remove the objects they created.
    # Restoring the former prefix here would break those older downgrade paths.
    return
