from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

APP_DATABASE_VARIABLE = "POSTGRES_TEST_DATABASE_URL"
MIGRATION_DATABASE_VARIABLE = "MIGRATION_DATABASE_URL"
BRANCH_NAME_VARIABLE = "POSTGRES_TEST_BRANCH_NAME"
DESTRUCTIVE_OPT_IN_VARIABLE = "ALLOW_DESTRUCTIVE_POSTGRES_TESTS"
APPROVED_POSTGRES_TEST_BRANCH = "backend-integration-test"
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
SECURE_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})
FORBIDDEN_BRANCH_NAMES = frozenset(
    {"main", "production", "prod", "development", "develop", "dev"}
)


class PostgresTestSafetyError(RuntimeError):
    """Raised without secret values when a test database is not proven safe."""


@dataclass(frozen=True, slots=True, repr=False)
class ApprovedPostgresTestEnvironment:
    """Validated URLs for later fixtures, with credential-safe rendering."""

    application_database_url: str = field(repr=False)
    migration_database_url: str | None = field(repr=False)
    branch_name: str
    destructive_allowed: bool

    def __repr__(self) -> str:
        return (
            "ApprovedPostgresTestEnvironment("
            f"branch_name={self.branch_name!r}, "
            f"destructive_allowed={self.destructive_allowed!r}, "
            "database_urls=<redacted>)"
        )


def validate_postgres_test_environment(
    environ: Mapping[str, str] | None = None,
    *,
    require_migration: bool = False,
    require_destructive: bool = False,
) -> ApprovedPostgresTestEnvironment:
    """Validate dedicated Neon test settings without opening a connection."""
    values = os.environ if environ is None else environ
    branch_name = values.get(BRANCH_NAME_VARIABLE, "")
    if not branch_name:
        _fail(f"{BRANCH_NAME_VARIABLE} is required")
    if branch_name.strip().lower() in FORBIDDEN_BRANCH_NAMES:
        _fail(f"{BRANCH_NAME_VARIABLE} identifies a forbidden environment")
    if branch_name != APPROVED_POSTGRES_TEST_BRANCH:
        _fail(
            f"{BRANCH_NAME_VARIABLE} must identify the approved dedicated "
            "PostgreSQL test branch"
        )

    destructive_allowed = values.get(DESTRUCTIVE_OPT_IN_VARIABLE) == "true"
    if require_destructive and not destructive_allowed:
        _fail(
            f"{DESTRUCTIVE_OPT_IN_VARIABLE} must be exactly true for "
            "destructive PostgreSQL tests"
        )
    if require_destructive:
        require_migration = True

    application_database_url = values.get(APP_DATABASE_VARIABLE, "")
    if not application_database_url:
        _fail(f"{APP_DATABASE_VARIABLE} is required")
    application_url = _validate_url(
        APP_DATABASE_VARIABLE,
        application_database_url,
        require_pooled=True,
    )

    migration_database_url = values.get(MIGRATION_DATABASE_VARIABLE) or None
    if require_migration and migration_database_url is None:
        _fail(f"{MIGRATION_DATABASE_VARIABLE} is required for migration tests")

    migration_url: URL | None = None
    if migration_database_url is not None:
        migration_url = _validate_url(
            MIGRATION_DATABASE_VARIABLE,
            migration_database_url,
            require_direct=True,
        )
        if _endpoint_identity(application_url) != _endpoint_identity(migration_url):
            _fail(
                f"{APP_DATABASE_VARIABLE} and {MIGRATION_DATABASE_VARIABLE} "
                "must target the same dedicated Neon test branch"
            )

    _reject_protected_database_reuse(
        values,
        application_url,
        migration_url,
    )

    return ApprovedPostgresTestEnvironment(
        application_database_url=application_database_url,
        migration_database_url=migration_database_url,
        branch_name=branch_name,
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
    driver_connection = getattr(
        getattr(connection, "connection", None),
        "driver_connection",
        connection,
    )
    connection_info = getattr(driver_connection, "info", None)
    if connection_info is None:
        _fail("Connected PostgreSQL identity is unavailable")

    actual_host = getattr(connection_info, "host", "")
    actual_database = getattr(connection_info, "dbname", "")
    tls_active = getattr(connection_info, "ssl_in_use", False)
    if _host_identity(actual_host) != _endpoint_identity(parsed_url):
        _fail("Connected PostgreSQL endpoint does not match the approved target")
    if actual_database != parsed_url.database:
        _fail("Connected PostgreSQL database does not match the approved target")
    if tls_active is not True:
        _fail("Connected PostgreSQL session must use TLS")


def _validate_url(
    variable_name: str,
    raw_url: str,
    *,
    require_pooled: bool = False,
    require_direct: bool = False,
) -> URL:
    try:
        parsed_url = make_url(raw_url)
    except (ArgumentError, TypeError, ValueError):
        raise PostgresTestSafetyError(
            f"{variable_name} must contain a valid PostgreSQL URL"
        ) from None

    if parsed_url.drivername not in POSTGRES_DRIVERS:
        _fail(f"{variable_name} must contain a PostgreSQL URL")

    hostname = (parsed_url.host or "").lower()
    if not hostname.endswith(".neon.tech"):
        _fail(f"{variable_name} must target Neon PostgreSQL")
    if parsed_url.query.get("sslmode") not in SECURE_SSL_MODES:
        _fail(f"{variable_name} must require PostgreSQL TLS")

    endpoint_name = hostname.partition(".")[0]
    is_pooled = endpoint_name.endswith("-pooler")
    if require_pooled and not is_pooled:
        _fail(f"{variable_name} must use a pooled Neon connection")
    if require_direct and is_pooled:
        _fail(f"{variable_name} must use a direct Neon connection")
    return parsed_url


def _reject_protected_database_reuse(
    values: Mapping[str, str],
    application_url: URL,
    migration_url: URL | None,
) -> None:
    test_identities = {_endpoint_identity(application_url)}
    if migration_url is not None:
        test_identities.add(_endpoint_identity(migration_url))

    for variable_name in PROTECTED_DATABASE_VARIABLES:
        raw_url = values.get(variable_name)
        if not raw_url:
            continue
        protected_url = _validate_url(
            variable_name,
            raw_url,
            require_pooled=True,
        )
        if _endpoint_identity(protected_url) in test_identities:
            _fail(
                "PostgreSQL tests must use a Neon branch separate from "
                "development and production"
            )


def _endpoint_identity(database_url: URL) -> str:
    return _host_identity(database_url.host or "")


def _host_identity(hostname: str) -> str:
    hostname = hostname.lower()
    endpoint_name, separator, remainder = hostname.partition(".")
    if endpoint_name.endswith("-pooler"):
        endpoint_name = endpoint_name.removesuffix("-pooler")
    return f"{endpoint_name}{separator}{remainder}"


def _fail(message: str) -> None:
    raise PostgresTestSafetyError(message)


__all__ = [
    "APPROVED_POSTGRES_TEST_BRANCH",
    "ApprovedPostgresTestEnvironment",
    "PostgresTestSafetyError",
    "validate_connected_postgres_test_environment",
    "validate_postgres_test_environment",
]
