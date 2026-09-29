"""Read-only PostgreSQL inventory and evidence fingerprints; never export rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from flask import Flask
from sqlalchemy import MetaData, Table, column, inspect, select, text
from sqlalchemy import table as sql_table
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

from app.config import validate_postgres_database_uri
from app.extensions import db
from app.models import (
    PolicyAssignmentChainHead,
    PolicyAssignmentEvent,
    PolicyRevision,
    PolicySynchronizationChainHead,
    PolicySynchronizationEvent,
    policy_revision_content_hash,
)
from app.services.audit_verification import (
    verify_policy_assignment_chain,
    verify_policy_synchronization_chain,
)


def canonical(value: Any) -> Any:
    """Stable typed representation; no lossy float/byte/time conversions."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return {"datetime": value.isoformat()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"bytes": bytes(value).hex()}
    if isinstance(value, UUID):
        return {"uuid": str(value)}
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if isinstance(value, dict):
        return {str(key): canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("Unsupported inventory value type")


def encoded(value: Any) -> bytes:
    return json.dumps(
        canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def query(connection: Connection, statement: str) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(text(statement)).mappings()]


def verify_audit() -> dict[str, int]:
    revisions = 0
    for revision in db.session.scalars(select(PolicyRevision)):
        if revision.content_hash != policy_revision_content_hash(revision.payload):
            raise ValueError("Policy revision hash verification failed")
        revisions += 1
    device_ids = set(db.session.scalars(select(PolicyAssignmentEvent.device_id)))
    device_ids.update(db.session.scalars(select(PolicyAssignmentChainHead.device_id)))
    for device_id in sorted(device_ids):
        verify_policy_assignment_chain(device_id)
    pseudonyms = set(
        db.session.scalars(
            select(PolicySynchronizationEvent.requested_device_pseudonym)
        )
    )
    pseudonyms.update(
        db.session.scalars(
            select(PolicySynchronizationChainHead.requested_device_pseudonym)
        )
    )
    for pseudonym in sorted(pseudonyms):
        verify_policy_synchronization_chain(pseudonym)
    return {
        "revisions": revisions,
        "assignment_chains": len(device_ids),
        "sync_chains": len(pseudonyms),
    }


def inventory(connection: Connection, *, fingerprints: bool) -> dict[str, Any]:
    inspector = inspect(connection)
    report: dict[str, Any] = {
        "format_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "server": query(
            connection,
            "SELECT version(), pg_database_size(current_database()) AS size_bytes",
        ),
        "settings": query(
            connection,
            "SELECT name, setting, unit FROM pg_settings WHERE name IN ('server_version_num','server_encoding','TimeZone','max_connections','search_path','default_transaction_read_only','transaction_read_only','default_transaction_isolation','statement_timeout','lock_timeout','idle_in_transaction_session_timeout') ORDER BY name",
        ),
        "schemas": inspector.get_schema_names(),
        "extensions": query(
            connection,
            "SELECT e.extname, e.extversion, n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace ORDER BY e.extname",
        ),
        "connections": query(
            connection,
            "SELECT backend_type, state, count(*) AS count FROM pg_stat_activity WHERE datname=current_database() GROUP BY backend_type,state ORDER BY backend_type,state",
        ),
        "tables": {},
        "sequences": [],
        "triggers": query(
            connection,
            "SELECT c.relname, t.tgname, t.tgenabled, pg_get_triggerdef(t.oid, true) AS definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname",
        ),
        "functions": query(
            connection,
            "SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS arguments, p.prosecdef, pg_get_functiondef(p.oid) AS definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'edug_%' ORDER BY p.proname,arguments",
        ),
        "grants": query(
            connection,
            "SELECT table_name, grantee, privilege_type FROM information_schema.table_privileges WHERE table_schema='public' ORDER BY table_name,grantee,privilege_type",
        ),
        "default_grants": query(
            connection,
            "SELECT COALESCE(n.nspname, '*') AS schema, d.defaclrole::regrole::text AS role, d.defaclobjtype, d.defaclacl::text FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace ORDER BY schema,role,d.defaclobjtype",
        ),
        "row_security": query(
            connection,
            "SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') ORDER BY c.relname",
        ),
    }
    tables = inspector.get_table_names(schema="public")
    report["missing_application_tables"] = sorted(set(db.metadata.tables) - set(tables))
    report["other_schemas"] = [
        name
        for name in report["schemas"]
        if name not in {"public", "information_schema"} and not name.startswith("pg_")
    ]
    for name in sorted(tables):
        table = Table(name, MetaData(), schema="public", autoload_with=connection)
        columns = [
            {
                "name": col.name,
                "type": str(col.type),
                "nullable": col.nullable,
                "default": str(getattr(col.server_default, "arg", ""))
                if col.server_default
                else None,
            }
            for col in table.columns
        ]
        entry: dict[str, Any] = {
            "columns": columns,
            "primary_key": inspector.get_pk_constraint(name, schema="public"),
            "foreign_keys": sorted(
                inspector.get_foreign_keys(name, schema="public"),
                key=lambda item: item["name"] or "",
            ),
            "checks": sorted(
                inspector.get_check_constraints(name, schema="public"),
                key=lambda item: item["name"] or "",
            ),
            "indexes": sorted(
                inspector.get_indexes(name, schema="public"),
                key=lambda item: item["name"],
            ),
            "unique_constraints": sorted(
                inspector.get_unique_constraints(name, schema="public"),
                key=lambda item: item["name"] or "",
            ),
        }
        if fingerprints:
            if not list(table.primary_key):
                raise ValueError(
                    "Cannot fingerprint a table without a stable primary key"
                )
            digest = hashlib.sha256()
            count = 0
            with connection.execute(
                select(table)
                .order_by(*table.primary_key)
                .execution_options(stream_results=True)
            ) as rows:
                for row in rows:
                    payload = encoded(tuple(row))
                    digest.update(len(payload).to_bytes(8, "big"))
                    digest.update(payload)
                    count += 1
            entry.update(row_count=count, sha256=digest.hexdigest())
        else:
            # Identifier quoting is handled by SQLAlchemy, never interpolation.
            from sqlalchemy import func

            entry["row_count"] = connection.scalar(
                select(func.count()).select_from(table)
            )
        report["tables"][name] = entry
    if "alembic_version" in tables:
        report["migration_heads"] = list(
            connection.execute(
                text(
                    "SELECT version_num FROM public.alembic_version ORDER BY version_num"
                )
            ).scalars()
        )
    else:
        report["migration_heads"] = []
    for name in sorted(inspector.get_sequence_names(schema="public")):
        sequence = sql_table(
            name, column("last_value"), column("is_called"), schema="public"
        )
        state = [dict(row) for row in connection.execute(select(sequence)).mappings()]
        report["sequences"].append({"name": name, "state": state})
    report["sequence_definitions"] = query(
        connection,
        "SELECT sequencename, data_type::text, start_value, min_value, max_value, increment_by, cycle, cache_size FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url-env",
        required=True,
        help="Name of an existing environment variable, not a URL",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fingerprints", action="store_true")
    parser.add_argument("--verify-audit", action="store_true")
    parser.add_argument(
        "--writers-stopped",
        action="store_true",
        help="Operator attests ALL writers are stopped; required for a final comparison",
    )
    arguments = parser.parse_args()
    try:
        url = validate_postgres_database_uri(
            "inventory connection", os.environ.get(arguments.url_env, "")
        )
        app = Flask("edug-read-only-inventory")
        app.config.update(
            SQLALCHEMY_DATABASE_URI=url,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": NullPool,
                "connect_args": {
                    "connect_timeout": 10,
                    "options": "-c default_transaction_read_only=on -c statement_timeout=60000 -c lock_timeout=5000",
                },
            },
        )
        db.init_app(app)
        with app.app_context():
            try:
                connection = db.session.connection()
                connection.exec_driver_sql(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                )
                driver_connection = connection.connection.driver_connection
                if driver_connection is None:
                    raise ValueError("Database connection identity unavailable")
                info = driver_connection.info
                if (
                    not info.ssl_in_use
                    or info.host != url.host
                    or info.dbname != url.database
                    or (url.username and info.user != url.username)
                ):
                    raise ValueError("Connected database identity or TLS mismatch")
                report = inventory(connection, fingerprints=arguments.fingerprints)
                report["tls_verified"] = url.query.get("sslmode") == "verify-full"
                report["writers_stopped"] = arguments.writers_stopped
                report["audit"] = verify_audit() if arguments.verify_audit else None
            finally:
                db.session.rollback()
                db.session.remove()
                db.engine.dispose()
        # Refuse accidental replacement of evidence from a previous capture.
        with arguments.output.open("x", encoding="utf-8") as output:
            json.dump(
                canonical(report), output, indent=2, sort_keys=True, allow_nan=False
            )
            output.write("\n")
        print(
            "Read-only inventory completed. Review the local report; no database rows were exported."
        )
        return 0
    except Exception as error:
        # Database exceptions may embed URLs, credentials and submitted values.
        print(
            f"Inventory failed ({type(error).__name__}); no readiness claim. Check configuration and permissions locally.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
