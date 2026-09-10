from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from app.config import database_project_identity, validate_postgres_database_uri

APP_DATABASE_VARIABLE = "POSTGRES_TEST_DATABASE_URL"
MIGRATION_DATABASE_VARIABLE = "MIGRATION_DATABASE_URL"
PURPOSE_VARIABLE = "POSTGRES_TEST_PURPOSE"
PROJECT_REF_VARIABLE = "POSTGRES_TEST_PROJECT_REF"
DESTRUCTIVE_OPT_IN_VARIABLE = "ALLOW_DESTRUCTIVE_POSTGRES_TESTS"
APPROVED_POSTGRES_TEST_PURPOSE = "backend-integration-test"
PROTECTED_DATABASE_VARIABLES = (
    "DEVELOPMENT_DATABASE_URL",
    "PRODUCTION_DATABASE_URL",
)
POSTGRES_DRIVERS = frozenset(
    {
        "postgres",
        "postgresql",
        "postgresql+psycopg2",
    }
)


class PostgresTestSafetyError(RuntimeError):
    """Raised without secret values when a test database is not proven safe."""


@dataclass(frozen=True, slots=True, repr=False)
class ApprovedPostgresTestEnvironment:
    """Validated URLs for later fixtures, with credential-safe rendering."""

    application_database_url: str = field(repr=False)
    migration_database_url: str | None = field(repr=False)
    purpose: str
    project_ref: str
    destructive_allowed: bool

    def __repr__(self) -> str:
        return (
            "ApprovedPostgresTestEnvironment("
            f"purpose={self.purpose!r}, "
            f"project_ref={self.project_ref!r}, "
            f"destructive_allowed={self.destructive_allowed!r}, "
            "database_urls=<redacted>)"
        )


def validate_postgres_test_environment(
    environ: Mapping[str, str] | None = None,
    *,
    require_migration: bool = False,
    require_destructive: bool = False,
) -> ApprovedPostgresTestEnvironment:
    """Validate a dedicated Supabase test project without opening a connection."""
    values = os.environ if environ is None else environ
    purpose = values.get(PURPOSE_VARIABLE, "")
    if purpose != APPROVED_POSTGRES_TEST_PURPOSE:
        _fail(
            f"{PURPOSE_VARIABLE} must identify the approved dedicated "
            "PostgreSQL test purpose"
        )

    project_ref = values.get(PROJECT_REF_VARIABLE, "").strip().lower()
    if not re.fullmatch(r"[a-z0-9]{20}", project_ref):
        _fail(f"{PROJECT_REF_VARIABLE} must contain a Supabase project reference")

    application_database_url = values.get(APP_DATABASE_VARIABLE, "")
    if not application_database_url:
        _fail(f"{APP_DATABASE_VARIABLE} is required")
    application_url = _validate_url(APP_DATABASE_VARIABLE, application_database_url)
    if database_project_identity(application_url) != project_ref:
        _fail(f"{APP_DATABASE_VARIABLE} must match the approved {PROJECT_REF_VARIABLE}")

    destructive_allowed = values.get(DESTRUCTIVE_OPT_IN_VARIABLE) == "true"
    if require_destructive and not destructive_allowed:
        _fail(
            f"{DESTRUCTIVE_OPT_IN_VARIABLE} must be exactly true for "
            "destructive PostgreSQL tests"
        )
    if require_destructive:
        require_migration = True

    migration_database_url = values.get(MIGRATION_DATABASE_VARIABLE) or None
    if require_migration and migration_database_url is None:
        _fail(f"{MIGRATION_DATABASE_VARIABLE} is required for migration tests")

    migration_url: URL | None = None
    if migration_database_url is not None:
        migration_url = _validate_url(
            MIGRATION_DATABASE_VARIABLE,
            migration_database_url,
        )
        if (
            database_project_identity(migration_url) != project_ref
            or migration_url.database != application_url.database
        ):
            _fail(
                f"{APP_DATABASE_VARIABLE} and {MIGRATION_DATABASE_VARIABLE} "
                "must target the same dedicated Supabase project and database"
            )

    _reject_protected_database_reuse(values, application_url, migration_url)

    return ApprovedPostgresTestEnvironment(
        application_database_url=application_database_url,
        migration_database_url=migration_database_url,
        purpose=purpose,
        project_ref=project_ref,
        destructive_allowed=destructive_allowed,
    )


def validate_connected_postgres_test_environment(
    connection: object,
    approved: ApprovedPostgresTestEnvironment,
    *,
    expected_database_url: str | None = None,
    require_destructive: bool = False,
) -> None:
    """Verify the actual libpq target without rendering connection details."""
    if require_destructive and not approved.destructive_allowed:
        _fail("Destructive PostgreSQL access has not been approved")

    configured_url = expected_database_url or approved.application_database_url
    parsed_url = _validate_url("approved PostgreSQL test URL", configured_url)
    approved_url = _validate_url(
        "approved application URL", approved.application_database_url
    )
    if (
        database_project_identity(parsed_url) != approved.project_ref
        or database_project_identity(approved_url) != approved.project_ref
        or parsed_url.database != approved_url.database
    ):
        _fail("Requested PostgreSQL project/database is outside the approved target")

    driver_connection = getattr(
        getattr(connection, "connection", None),
        "driver_connection",
        connection,
    )
    connection_info = getattr(driver_connection, "info", None)
    if connection_info is None:
        _fail("Connected PostgreSQL identity is unavailable")

    if (
        getattr(connection_info, "host", "") != parsed_url.host
        or getattr(connection_info, "user", None) != parsed_url.username
        or str(getattr(connection_info, "port", "")) != str(parsed_url.port or 5432)
    ):
        _fail("Connected PostgreSQL endpoint or tenant does not match approval")
    if getattr(connection_info, "dbname", "") != parsed_url.database:
        _fail("Connected PostgreSQL database does not match the approved target")
    if getattr(connection_info, "ssl_in_use", False) is not True:
        _fail("Connected PostgreSQL session must use TLS")


def _validate_url(variable_name: str, raw_url: str) -> URL:
    try:
        parsed_url = make_url(raw_url)
    except (ArgumentError, TypeError, ValueError):
        raise PostgresTestSafetyError(
            f"{variable_name} must contain a valid PostgreSQL URL"
        ) from None

    if parsed_url.drivername not in POSTGRES_DRIVERS:
        _fail(f"{variable_name} must contain a PostgreSQL URL")

    try:
        return validate_postgres_database_uri(variable_name, raw_url)
    except RuntimeError as error:
        raise PostgresTestSafetyError(str(error)) from None


def _reject_protected_database_reuse(
    values: Mapping[str, str],
    application_url: URL,
    migration_url: URL | None,
) -> None:
    test_projects = {database_project_identity(application_url)}
    if migration_url is not None:
        test_projects.add(database_project_identity(migration_url))

    for variable_name in PROTECTED_DATABASE_VARIABLES:
        raw_url = values.get(variable_name)
        if not raw_url:
            continue
        protected_url = _validate_url(variable_name, raw_url)
        if database_project_identity(protected_url) in test_projects:
            _fail(
                "PostgreSQL tests must use a Supabase project separate from "
                "development and production"
            )


def _fail(message: str) -> None:
    raise PostgresTestSafetyError(message)


__all__ = [
    "APPROVED_POSTGRES_TEST_PURPOSE",
    "ApprovedPostgresTestEnvironment",
    "PostgresTestSafetyError",
    "validate_connected_postgres_test_environment",
    "validate_postgres_test_environment",
]
