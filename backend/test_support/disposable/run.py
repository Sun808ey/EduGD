"""Bootstrap only the guarded disposable database, then run integration tests."""

import socket
import time

import pytest
from flask_migrate import upgrade
from sqlalchemy import create_engine, text

from app import create_app
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

DATABASE_HOST = "db.eduglocaltest0000001.supabase.co"


def _wait_for_internal_dns(timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            socket.gethostbyname(DATABASE_HOST)
            return
        except OSError as error:
            last_error = error
            time.sleep(0.25)
    raise RuntimeError(
        f"isolated Docker DNS did not resolve {DATABASE_HOST}: {last_error}"
    )


def main() -> int:
    _wait_for_internal_dns()
    approved = validate_postgres_test_environment(
        require_migration=True, require_destructive=True
    )
    engine = create_engine(approved.application_database_url)
    try:
        with engine.connect() as connection:
            validate_connected_postgres_test_environment(
                connection, approved, require_destructive=True
            )
            connection.execute(
                text(
                    """DO $$ DECLARE role_name text; BEGIN
                    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role', 'edug_runtime'] LOOP
                        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                            EXECUTE format('CREATE ROLE %I NOLOGIN', role_name);
                        END IF;
                    END LOOP;
                    END $$"""
                )
            )
            connection.commit()
    finally:
        engine.dispose()
    application = create_app("postgres-testing")
    with application.app_context():
        upgrade()
    return pytest.main(["-m", "postgres or migration or concurrency"])


if __name__ == "__main__":
    raise SystemExit(main())
