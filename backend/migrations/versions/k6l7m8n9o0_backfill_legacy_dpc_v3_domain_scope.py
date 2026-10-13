"""Backfill the web-filter scope required by the hardened DPC v3 contract.

Revision ID: k6l7m8n9o0
Revises: j5k6l7m8n9
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "k6l7m8n9o0"
down_revision = "j5k6l7m8n9"
branch_labels = None
depends_on = None

MIGRATION_ACTOR = "migration:j5k6l7m8n9-to-k6l7m8n9o0"


def _decoded_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _backfilled_payload(value: Any) -> dict[str, Any] | None:
    payload = _decoded_json(value)
    if not isinstance(payload, dict) or payload.get("schema_version") != 3:
        return None

    web_filter = payload.get("web_filter")
    if not isinstance(web_filter, dict) or not isinstance(
        web_filter.get("rules"), list
    ):
        return None

    missing_scope = any(
        isinstance(rule, dict) and "include_subdomains" not in rule
        for rule in web_filter["rules"]
    )
    if not missing_scope:
        return None

    upgraded = dict(payload)
    upgraded_web_filter = dict(web_filter)
    upgraded_web_filter["rules"] = [
        {
            **rule,
            # The legacy v3 contract matched a domain and its web namespace;
            # preserve that behaviour when materialising the explicit field.
            "include_subdomains": True,
        }
        if isinstance(rule, dict) and "include_subdomains" not in rule
        else rule
        for rule in web_filter["rules"]
    ]
    upgraded["web_filter"] = upgraded_web_filter
    return upgraded


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {
            unicodedata.normalize("NFC", key): _canonical_value(item)
            for key, item in value.items()
        }
    raise ValueError("policy payload cannot be canonically encoded")


def _content_hash(payload: dict[str, Any]) -> bytes:
    encoded = json.dumps(
        _canonical_value(payload),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).digest()


def upgrade() -> None:
    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.text(
                "SELECT policy_id, version, payload "
                "FROM policy_revisions ORDER BY policy_id, version DESC"
            )
        )
    )

    latest_by_policy: dict[int, Any] = {}
    for row in rows:
        latest_by_policy.setdefault(row.policy_id, row)

    revision_table = sa.table(
        "policy_revisions",
        sa.column("revision_uuid", sa.Uuid()),
        sa.column("policy_id", sa.Integer()),
        sa.column("version", sa.Integer()),
        sa.column("payload", sa.JSON()),
        sa.column("content_hash", sa.LargeBinary()),
        sa.column("created_by", sa.String()),
    )
    for row in latest_by_policy.values():
        payload = _backfilled_payload(row.payload)
        if payload is None:
            continue
        connection.execute(
            revision_table.insert().values(
                revision_uuid=uuid4(),
                policy_id=row.policy_id,
                version=row.version + 1,
                payload=payload,
                content_hash=_content_hash(payload),
                created_by=MIGRATION_ACTOR,
            )
        )


def downgrade() -> None:
    # Policy revisions are immutable audit evidence; successor rows remain in
    # place on downgrade rather than attempting an unsafe deletion.
    pass
