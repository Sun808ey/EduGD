"""Bootstrap only the guarded disposable database, then run integration tests."""

import subprocess
import sys

from flask_migrate import upgrade
from sqlalchemy import create_engine

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
    finally:
        engine.dispose()
    application = create_app("postgres-testing")
    with application.app_context():
        upgrade()
    return subprocess.call(
        [sys.executable, "-m", "pytest", "-m", "postgres or migration or concurrency"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
