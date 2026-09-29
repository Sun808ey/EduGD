"""Enforce blocked-app JSON integrity.

Revision ID: f4a7c9e2b6d1
Revises: d3f6a8b1c4e9
Create Date: 2026-07-23 09:30:00.000000

"""

from alembic import op

revision = "f4a7c9e2b6d1"
down_revision = "d3f6a8b1c4e9"
branch_labels = None
depends_on = None

POSTGRES_VALIDATOR_FUNCTION = r"""
CREATE FUNCTION edug_valid_blocked_apps(value json)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN json_typeof(value) <> 'array' THEN FALSE
        ELSE
            NOT EXISTS (
                SELECT 1
                FROM json_array_elements(value) AS element
                WHERE json_typeof(element) <> 'string'
                   OR (element #>> '{}')
                      !~ '^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$'
            )
            AND (
                SELECT count(*) = count(DISTINCT element #>> '{}')
                FROM json_array_elements(value) AS element
            )
    END
$function$
"""


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(POSTGRES_VALIDATOR_FUNCTION)
    op.create_check_constraint(
        "ck_policies_blocked_apps",
        "policies",
        "edug_valid_blocked_apps(blocked_apps)",
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_constraint(
        "ck_policies_blocked_apps",
        "policies",
        type_="check",
    )
    op.execute("DROP FUNCTION edug_valid_blocked_apps(json)")
