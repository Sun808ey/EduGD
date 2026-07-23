from pathlib import Path
from typing import cast

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask_migrate import downgrade, upgrade
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

from app import create_app
from app.extensions import db
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

pytestmark = [pytest.mark.postgres, pytest.mark.migration]
MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"
HEAD_REVISION = "a8d5e2f7c1b4"


def _script_directory() -> ScriptDirectory:
    configuration = Config(str(MIGRATIONS_DIRECTORY / "alembic.ini"))
    configuration.set_main_option(
        "script_location",
        str(MIGRATIONS_DIRECTORY),
    )
    return ScriptDirectory.from_config(configuration)


def _current_revision(connection: Connection) -> str | None:
    if not inspect(connection).has_table("alembic_version"):
        return None
    return cast(
        str | None,
        connection.scalar(text("SELECT version_num FROM alembic_version")),
    )


def test_migration_history_is_one_linear_twelve_revision_chain() -> None:
    script = _script_directory()
    revisions = list(script.walk_revisions())

    assert script.get_heads() == [HEAD_REVISION]
    assert [revision.revision for revision in revisions] == [
        "a8d5e2f7c1b4",
        "f4a7c9e2b6d1",
        "d3f6a8b1c4e9",
        "e7c4a9b2d6f1",
        "f2a9d4c7e1b3",
        "c6f8a2d4e7b1",
        "b4e7c1d3f5a9",
        "9d2f4a6c8e10",
        "7c91b8e2d4a6",
        "3a6f4a9eb4f2",
        "203748fda298",
        "a2b94c33c0a3",
    ]
    assert revisions[-1].down_revision is None


def test_full_migration_upgrade_downgrade_upgrade_cycle() -> None:
    approved = validate_postgres_test_environment(
        require_migration=True,
        require_destructive=True,
    )
    assert approved.migration_database_url is not None
    application = create_app("postgres-testing")
    migration_engine = create_engine(
        approved.migration_database_url,
        poolclass=NullPool,
    )

    with migration_engine.connect() as connection:
        validate_connected_postgres_test_environment(
            connection,
            approved,
            expected_database_url=approved.migration_database_url,
            require_destructive=True,
        )

    try:
        with application.app_context():
            downgrade(directory=str(MIGRATIONS_DIRECTORY), revision="base")
            upgrade(directory=str(MIGRATIONS_DIRECTORY), revision="head")
        with migration_engine.connect() as connection:
            assert _current_revision(connection) == HEAD_REVISION

        with application.app_context():
            downgrade(directory=str(MIGRATIONS_DIRECTORY), revision="base")
        with migration_engine.connect() as connection:
            assert _current_revision(connection) is None

        with application.app_context():
            upgrade(directory=str(MIGRATIONS_DIRECTORY), revision="head")
        with migration_engine.connect() as connection:
            assert _current_revision(connection) == HEAD_REVISION
    finally:
        with migration_engine.connect() as connection:
            needs_restore = _current_revision(connection) != HEAD_REVISION
        if needs_restore:
            with application.app_context():
                upgrade(directory=str(MIGRATIONS_DIRECTORY), revision="head")

    with application.app_context():
        with migration_engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            assert compare_metadata(migration_context, db.metadata) == []
    migration_engine.dispose()
