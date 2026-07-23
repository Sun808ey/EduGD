"""Create immutable policy revisions and bind assignments to exact revisions.

Revision ID: a8d5e2f7c1b4
Revises: f4a7c9e2b6d1
Create Date: 2026-07-23 15:00:00.000000

"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "a8d5e2f7c1b4"
down_revision = "f4a7c9e2b6d1"
branch_labels = None
depends_on = None

MIGRATION_ACTOR = "migration:f4a7c9e2b6d1-to-policy-revisions"
PACKAGE_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
)

POSTGRES_PAYLOAD_VALIDATOR = r"""
CREATE FUNCTION edug_valid_policy_revision_payload(value json)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN json_typeof(value) <> 'object' THEN FALSE
        WHEN (SELECT count(*) FROM json_object_keys(value)) <> 2 THEN FALSE
        WHEN value->'schema_version' IS NULL
          OR value->'blocked_apps' IS NULL THEN FALSE
        WHEN json_typeof(value->'schema_version') <> 'number' THEN FALSE
        WHEN (value->>'schema_version')::integer <> 1 THEN FALSE
        ELSE edug_valid_blocked_apps(value->'blocked_apps')
    END
$function$
"""

POSTGRES_IMMUTABILITY_FUNCTION = r"""
CREATE FUNCTION edug_reject_policy_revision_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION 'policy revisions are immutable'
        USING ERRCODE = '55000';
END
$function$
"""


def _decoded_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _valid_blocked_apps(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(set(value))
        and all(
            isinstance(item, str) and PACKAGE_PATTERN.fullmatch(item) is not None
            for item in value
        )
    )


def _payload(blocked_apps: Any) -> dict[str, Any]:
    value = _decoded_json(blocked_apps)
    if not _valid_blocked_apps(value):
        raise RuntimeError(
            "immutable policy revision preflight failed: invalid legacy payload"
        )
    return {"schema_version": 1, "blocked_apps": list(value)}


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise RuntimeError("immutable policy revision preflight failed: invalid timestamp")


def _preflight_upgrade(connection: sa.Connection) -> list[sa.Row[Any]]:
    policies = list(
        connection.execute(
            sa.text(
                "SELECT id, version, blocked_apps, created_at "
                "FROM policies ORDER BY id"
            )
        )
    )
    for policy in policies:
        if not isinstance(policy.version, int) or policy.version < 1:
            raise RuntimeError(
                "immutable policy revision preflight failed: invalid version"
            )
        _payload(policy.blocked_apps)

    mismatch_count = connection.scalar(
        sa.text(
            "SELECT count(*) FROM device_policy_assignments AS assignment "
            "LEFT JOIN policies AS policy ON policy.id = assignment.policy_id "
            "WHERE policy.id IS NULL "
            "OR assignment.policy_version <> policy.version"
        )
    )
    if mismatch_count:
        raise RuntimeError(
            "immutable policy revision preflight failed: "
            "legacy assignment history is not reconstructable"
        )
    return policies


def upgrade() -> None:
    connection = op.get_bind()
    policies = _preflight_upgrade(connection)
    is_postgresql = connection.dialect.name == "postgresql"

    if is_postgresql:
        op.execute(POSTGRES_PAYLOAD_VALIDATOR)

    payload_constraint = sa.CheckConstraint(
        "edug_valid_policy_revision_payload(payload)",
        name="ck_policy_revisions_payload",
    )
    if not is_postgresql:
        payload_constraint = payload_constraint.ddl_if(dialect="postgresql")

    op.create_table(
        "policy_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("revision_uuid", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "length(content_hash) = 32",
            name="ck_policy_revisions_content_hash_length",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_policy_revisions_version_positive",
        ),
        payload_constraint,
        *(
            (
                sa.ForeignKeyConstraint(
                    ["policy_id"],
                    ["policies.id"],
                    name="fk_policy_revisions_policy_id",
                    ondelete="RESTRICT",
                ),
            )
            if is_postgresql
            else ()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_id",
            "content_hash",
            name="uq_policy_revisions_policy_content_hash",
        ),
        sa.UniqueConstraint(
            "policy_id",
            "version",
            name="uq_policy_revisions_policy_version",
        ),
        sa.UniqueConstraint(
            "revision_uuid",
            name="uq_policy_revisions_revision_uuid",
        ),
    )
    op.create_index(
        "ix_policy_revisions_policy_created",
        "policy_revisions",
        ["policy_id", "created_at"],
    )

    revision_table = sa.table(
        "policy_revisions",
        sa.column("id", sa.Integer()),
        sa.column("revision_uuid", sa.Uuid()),
        sa.column("policy_id", sa.Integer()),
        sa.column("version", sa.Integer()),
        sa.column("payload", sa.JSON()),
        sa.column("content_hash", sa.LargeBinary()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("created_by", sa.String()),
    )
    revision_by_policy: dict[int, int] = {}
    for policy in policies:
        payload = _payload(policy.blocked_apps)
        revision_id = connection.scalar(
            revision_table.insert()
            .values(
                revision_uuid=uuid4(),
                policy_id=policy.id,
                version=policy.version,
                payload=payload,
                content_hash=hashlib.sha256(_canonical_bytes(payload)).digest(),
                created_at=_timestamp(policy.created_at),
                created_by=MIGRATION_ACTOR,
            )
            .returning(revision_table.c.id)
        )
        if not isinstance(revision_id, int):
            raise RuntimeError("immutable policy revision conversion failed")
        revision_by_policy[policy.id] = revision_id

    revision_count = connection.scalar(sa.text("SELECT count(*) FROM policy_revisions"))
    if revision_count != len(policies):
        raise RuntimeError("immutable policy revision row-count verification failed")

    with op.batch_alter_table("device_policy_assignments") as batch_op:
        batch_op.add_column(
            sa.Column("policy_revision_id", sa.Integer(), nullable=True)
        )
    for policy_id, revision_id in revision_by_policy.items():
        connection.execute(
            sa.text(
                "UPDATE device_policy_assignments "
                "SET policy_revision_id = :revision_id "
                "WHERE policy_id = :policy_id"
            ),
            {"revision_id": revision_id, "policy_id": policy_id},
        )
    if connection.scalar(
        sa.text(
            "SELECT count(*) FROM device_policy_assignments "
            "WHERE policy_revision_id IS NULL"
        )
    ):
        raise RuntimeError("immutable assignment conversion failed")

    op.drop_index(
        "ix_device_policy_assignments_policy_id",
        table_name="device_policy_assignments",
    )
    with op.batch_alter_table("device_policy_assignments") as batch_op:
        batch_op.alter_column(
            "policy_revision_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        if is_postgresql:
            batch_op.create_foreign_key(
                "fk_device_policy_assignments_policy_revision_id",
                "policy_revisions",
                ["policy_revision_id"],
                ["id"],
                ondelete="RESTRICT",
            )
        batch_op.drop_constraint(
            "ck_device_policy_assignments_version_positive",
            type_="check",
        )
        batch_op.drop_column("policy_version")
        batch_op.drop_column("policy_id")
    op.create_index(
        "ix_device_policy_assignments_policy_revision_id",
        "device_policy_assignments",
        ["policy_revision_id"],
    )

    if is_postgresql:
        op.drop_constraint(
            "ck_policies_blocked_apps",
            "policies",
            type_="check",
        )
    with op.batch_alter_table("policies") as batch_op:
        batch_op.drop_constraint("ck_policies_version_positive", type_="check")
        batch_op.drop_column("blocked_apps")
        batch_op.drop_column("version")

    if not is_postgresql:
        with op.batch_alter_table("policy_revisions") as batch_op:
            batch_op.create_foreign_key(
                "fk_policy_revisions_policy_id",
                "policies",
                ["policy_id"],
                ["id"],
                ondelete="RESTRICT",
            )
        with op.batch_alter_table("device_policy_assignments") as batch_op:
            batch_op.create_foreign_key(
                "fk_device_policy_assignments_policy_revision_id",
                "policy_revisions",
                ["policy_revision_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    if is_postgresql:
        op.execute(POSTGRES_IMMUTABILITY_FUNCTION)
        op.execute(
            "CREATE TRIGGER trg_policy_revisions_immutable "
            "BEFORE UPDATE OR DELETE ON policy_revisions "
            "FOR EACH ROW EXECUTE FUNCTION "
            "edug_reject_policy_revision_mutation()"
        )


def _preflight_downgrade(connection: sa.Connection) -> list[sa.Row[Any]]:
    policies = list(
        connection.execute(
            sa.text(
                "SELECT policy.id AS policy_id, revision.id AS revision_id, "
                "revision.version, revision.payload, revision.content_hash "
                "FROM policies AS policy "
                "LEFT JOIN policy_revisions AS revision "
                "ON revision.policy_id = policy.id "
                "ORDER BY policy.id"
            )
        )
    )
    counts: dict[int, int] = {}
    for row in policies:
        counts[row.policy_id] = counts.get(row.policy_id, 0) + (
            0 if row.revision_id is None else 1
        )
    if any(count != 1 for count in counts.values()):
        raise RuntimeError(
            "immutable policy revision downgrade refused: "
            "every policy must have exactly one revision"
        )

    for row in policies:
        payload = _decoded_json(row.payload)
        if (
            not isinstance(payload, dict)
            or set(payload) != {"schema_version", "blocked_apps"}
            or payload.get("schema_version") != 1
            or not _valid_blocked_apps(payload.get("blocked_apps"))
            or hashlib.sha256(_canonical_bytes(payload)).digest()
            != bytes(row.content_hash)
        ):
            raise RuntimeError(
                "immutable policy revision downgrade refused: "
                "invalid revision evidence"
            )

    invalid_assignments = connection.scalar(
        sa.text(
            "SELECT count(*) FROM device_policy_assignments AS assignment "
            "JOIN policy_revisions AS assigned_revision "
            "ON assigned_revision.id = assignment.policy_revision_id "
            "WHERE EXISTS ("
            "SELECT 1 FROM policy_revisions AS other_revision "
            "WHERE other_revision.policy_id = assigned_revision.policy_id "
            "AND other_revision.id <> assigned_revision.id)"
        )
    )
    if invalid_assignments:
        raise RuntimeError(
            "immutable policy revision downgrade refused: "
            "assignment does not reference the sole revision"
        )
    return policies


def downgrade() -> None:
    connection = op.get_bind()
    policies = _preflight_downgrade(connection)
    is_postgresql = connection.dialect.name == "postgresql"

    if is_postgresql:
        op.execute(
            "DROP TRIGGER trg_policy_revisions_immutable ON policy_revisions"
        )
        op.execute("DROP FUNCTION edug_reject_policy_revision_mutation()")

    with op.batch_alter_table("device_policy_assignments") as batch_op:
        batch_op.add_column(sa.Column("policy_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "policy_version",
                sa.Integer(),
                nullable=True,
                server_default="1",
            )
        )
    connection.execute(
        sa.text(
            "UPDATE device_policy_assignments AS assignment "
            "SET policy_id = revision.policy_id, "
            "policy_version = revision.version "
            "FROM policy_revisions AS revision "
            "WHERE revision.id = assignment.policy_revision_id"
        )
        if is_postgresql
        else sa.text(
            "UPDATE device_policy_assignments "
            "SET policy_id = (SELECT policy_id FROM policy_revisions "
            "WHERE id = device_policy_assignments.policy_revision_id), "
            "policy_version = (SELECT version FROM policy_revisions "
            "WHERE id = device_policy_assignments.policy_revision_id)"
        )
    )
    if connection.scalar(
        sa.text(
            "SELECT count(*) FROM device_policy_assignments "
            "WHERE policy_id IS NULL OR policy_version IS NULL"
        )
    ):
        raise RuntimeError("legacy assignment restoration failed")

    op.drop_index(
        "ix_device_policy_assignments_policy_revision_id",
        table_name="device_policy_assignments",
    )
    with op.batch_alter_table("device_policy_assignments") as batch_op:
        batch_op.alter_column(
            "policy_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "policy_version",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="1",
        )
        batch_op.create_check_constraint(
            "ck_device_policy_assignments_version_positive",
            "policy_version >= 1",
        )
        batch_op.drop_constraint(
            "fk_device_policy_assignments_policy_revision_id",
            type_="foreignkey",
        )
        batch_op.drop_column("policy_revision_id")
    op.create_index(
        "ix_device_policy_assignments_policy_id",
        "device_policy_assignments",
        ["policy_id"],
    )

    op.drop_index(
        "ix_policy_revisions_policy_created",
        table_name="policy_revisions",
    )
    op.drop_table("policy_revisions")
    if is_postgresql:
        op.execute("DROP FUNCTION edug_valid_policy_revision_payload(json)")

    with op.batch_alter_table("policies") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("blocked_apps", sa.JSON(), nullable=True))
    for row in policies:
        payload = _decoded_json(row.payload)
        connection.execute(
            sa.text(
                "UPDATE policies SET version = :version, "
                "blocked_apps = :blocked_apps WHERE id = :policy_id"
            ).bindparams(
                sa.bindparam("blocked_apps", type_=sa.JSON()),
            ),
            {
                "version": row.version,
                "blocked_apps": payload["blocked_apps"],
                "policy_id": row.policy_id,
            },
        )
    with op.batch_alter_table("policies") as batch_op:
        batch_op.alter_column(
            "version",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="1",
        )
        batch_op.alter_column(
            "blocked_apps",
            existing_type=sa.JSON(),
            nullable=False,
            server_default="[]",
        )
        batch_op.create_check_constraint(
            "ck_policies_version_positive",
            "version >= 1",
        )
    if is_postgresql:
        op.create_check_constraint(
            "ck_policies_blocked_apps",
            "policies",
            "edug_valid_blocked_apps(blocked_apps)",
        )

    with op.batch_alter_table("device_policy_assignments") as batch_op:
        batch_op.create_foreign_key(
            "fk_device_policy_assignments_policy_id",
            "policies",
            ["policy_id"],
            ["id"],
            ondelete="RESTRICT",
        )
