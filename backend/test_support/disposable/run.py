"""Bootstrap only the guarded disposable database, then run integration tests."""

import pytest
from flask_migrate import upgrade
from sqlalchemy import create_engine, text

from app import create_app
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)


def main() -> int:
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
