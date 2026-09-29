from __future__ import annotations

from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from flask import Flask
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[2] / "migrations"
ESSENTIAL_CONFIGURATION = (
    "APP_ENV",
    "SQLALCHEMY_DATABASE_URI",
    "SECRET_KEY",
    "JWT_SECRET_KEY",
)


class ReadinessCheckError(RuntimeError):
    """Indicate that an application dependency is not ready."""


def check_readiness(app: Flask) -> None:
    """Fail when essential configuration, database, or migrations are not ready."""
    _validate_essential_configuration(app)
    expected_heads = _expected_migration_heads()

    try:
        with db.engine.connect() as connection:
            if connection.dialect.name == "postgresql":
                timeout_ms = app.config["READINESS_STATEMENT_TIMEOUT_MS"]
                connection.execute(
                    text(
                        "SELECT set_config("  # noqa: S608 - static SQL statement
                        "'statement_timeout', :timeout, true)"
                    ),
                    {"timeout": f"{timeout_ms}ms"},
                )
            probe_result = connection.execute(text("SELECT 1")).scalar_one()
            database_heads = frozenset(
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalars()
            )
    except SQLAlchemyError:
        raise ReadinessCheckError("Database readiness check failed") from None

    if probe_result != 1:
        raise ReadinessCheckError("Database readiness probe returned an invalid result")
    if not expected_heads or database_heads != expected_heads:
        raise ReadinessCheckError("Database migration revision is not current")
    if app.config["APP_ENV"] == "production":
        try:
            Redis.from_url(
                app.config["RATELIMIT_STORAGE_URI"],
                socket_connect_timeout=3,
                socket_timeout=3,
            ).ping()
        except (RedisError, ValueError, OSError, TypeError):
            raise ReadinessCheckError("Rate-limit storage is unavailable") from None


def _validate_essential_configuration(app: Flask) -> None:
    missing = [
        setting
        for setting in ESSENTIAL_CONFIGURATION
        if not isinstance(app.config.get(setting), str)
        or not app.config[setting].strip()
    ]
    if missing:
        raise ReadinessCheckError("Essential application configuration is unavailable")


def _expected_migration_heads() -> frozenset[str]:
    configuration = AlembicConfig(str(MIGRATIONS_DIRECTORY / "alembic.ini"))
    configuration.set_main_option("script_location", str(MIGRATIONS_DIRECTORY))
    return frozenset(ScriptDirectory.from_config(configuration).get_heads())


__all__ = ["ReadinessCheckError", "check_readiness"]
