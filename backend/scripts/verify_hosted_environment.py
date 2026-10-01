"""One-shot hosted verification; never prints environment values or exceptions."""

import json
import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from app.deployment_identity import validate_deployment_identity
from app.extensions import db

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"


def repository_migration_head() -> str:
    """Return the single migration head shipped with this artifact."""
    configuration = Config(str(MIGRATIONS_DIRECTORY / "alembic.ini"))
    configuration.set_main_option("script_location", str(MIGRATIONS_DIRECTORY))
    heads = ScriptDirectory.from_config(configuration).get_heads()
    if len(heads) != 1:
        raise RuntimeError("repository must contain exactly one migration head")
    return heads[0]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    stage = "deployment_identity"
    try:
        validate_deployment_identity(os.environ)
        stage = "migration_contract"
        expected_migration_head = repository_migration_head()
        stage = "application_startup"
        app = create_app("production")
        stage = "database_connection"
        with app.app_context(), db.engine.connect() as connection:
            stage = "database_runtime_role"
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            require(
                connection.execute(text("SELECT current_user")).scalar()
                == "edug_runtime",
                "unexpected database runtime role",
            )
            stage = "database_tls"
            require(
                connection.execute(
                    text("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
                ).scalar()
                is True,
                "database TLS is not enabled",
            )
            stage = "database_revision"
            require(
                connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalar_one()
                == expected_migration_head,
                "unexpected Alembic revision",
            )
            stage = "database_read_permissions"
            existing_tables = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    )
                )
            }
            for table in db.metadata.sorted_tables:
                # The translation cache may be absent only when the hosted
                # target predates that repository migration.
                if (
                    table.name == "translation_cache_entries"
                    and table.name not in existing_tables
                ):
                    continue
                connection.execute(table.select().limit(0))
        stage = "readiness"
        require(
            app.test_client().get("/api/v1/ready").status_code == 200,
            "readiness check failed",
        )
    except Exception as error:
        result = {"hosted_verification": "FAIL", "stage": stage}
        if stage == "database_connection":
            expected_ca = "/app/certs/supabase-ca.pem"
            result["bundled_ca"] = (
                "present" if Path(expected_ca).is_file() else "absent"
            )
            configured_ca = make_url(os.environ["PRODUCTION_DATABASE_URL"]).query.get(
                "sslrootcert", os.environ.get("PGSSLROOTCERT")
            )
            result["ca_path"] = (
                "matches_bundle" if configured_ca == expected_ca else "different"
            )
            # Match known driver diagnostics, but never emit their raw text.
            diagnostic = str(error).lower()
            result["reason"] = "connection_failed"
            for fragment, reason in (
                ("root certificate file", "ca_file_unavailable"),
                ("certificate verify failed", "certificate_verification_failed"),
                ("password authentication failed", "authentication_failed"),
                ("tenant or user not found", "pooler_user_not_found"),
                ("network is unreachable", "network_unreachable"),
                ("could not translate host name", "dns_failed"),
                ("timeout expired", "connection_timeout"),
            ):
                if fragment in diagnostic:
                    result["reason"] = reason
                    break
        print(json.dumps(result), flush=True)
        return 1
    print(json.dumps({"hosted_verification": "PASS"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
