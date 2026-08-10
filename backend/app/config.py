from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIRECTORY = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIRECTORY / ".env", override=False)

NEON_HOST_SUFFIX = ".neon.tech"
SECURE_POSTGRES_SSL_MODES = frozenset(
    {
        "require",
        "verify-ca",
        "verify-full",
    }
)
APPLICATION_DATABASE_ENVIRONMENTS = (
    ("DEVELOPMENT_DATABASE_URL", True),
    ("POSTGRES_TEST_DATABASE_URL", False),
    ("PRODUCTION_DATABASE_URL", True),
)
POSTGRES_CONNECTION_TIMEOUT_SECONDS = 3
POSTGRES_ENGINE_OPTIONS: dict[str, object] = {
    "connect_args": {"connect_timeout": POSTGRES_CONNECTION_TIMEOUT_SECONDS},
    "pool_pre_ping": True,
    "pool_timeout": POSTGRES_CONNECTION_TIMEOUT_SECONDS,
}


def _environment_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_uri(database_uri: str) -> str:
    if database_uri.startswith("postgres://"):
        return database_uri.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1,
        )
    return database_uri


class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    ADMIN_AUDIT_PSEUDONYM_KEY = os.getenv("ADMIN_AUDIT_PSEUDONYM_KEY")
    POLICY_SYNC_AUDIT_KEY = os.getenv("POLICY_SYNC_AUDIT_KEY")
    PAIRING_TOKEN_PEPPER = os.getenv("PAIRING_TOKEN_PEPPER")
    PAIRING_TOKEN_PEPPER_VERSION = int(os.getenv("PAIRING_TOKEN_PEPPER_VERSION", "1"))
    PAIRING_TOKEN_PEPPERS: dict[int, str] | None = None
    DEVICE_ENROLLMENT_MODE = os.getenv("DEVICE_ENROLLMENT_MODE", "legacy").lower()
    ENROLLMENT_ADMIN_ENABLED = _environment_flag("ENROLLMENT_ADMIN_ENABLED")
    JWT_ALGORITHM = "HS256"
    JWT_DECODE_ALGORITHMS = ["HS256"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_TOKEN_LOCATION = ("headers",)
    JWT_HEADER_TYPE = "Bearer"
    JWT_ENCODE_ISSUER = "edug-school-policy-api"
    JWT_DECODE_ISSUER = "edug-school-policy-api"
    JWT_ENCODE_AUDIENCE = "edug-school-administration"
    JWT_DECODE_AUDIENCE = "edug-school-administration"
    SQLALCHEMY_DATABASE_URI: str | None = None
    SQLALCHEMY_ENGINE_OPTIONS: dict[str, object] = {}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_ENV_VAR: str | None = None
    REQUIRE_POOLED_DATABASE_URL = False
    LOG_LEVEL = "INFO"
    RATELIMIT_DEFAULT: list[str] = []
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI: str | None = "memory://"
    REDIS_URL = os.getenv("REDIS_URL")
    TRUSTED_PROXY_HOPS = 0
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    SENTRY_ERROR_SAMPLE_RATE = 0.25
    SENTRY_TRACES_SAMPLE_RATE = 0.01
    READINESS_STATEMENT_TIMEOUT_MS = 2_000
    MAX_CONTENT_LENGTH = 1 * 1_024 * 1_024
    REGISTRATION_MAX_CONTENT_LENGTH = 16 * 1_024
    ADMIN_AUTH_MAX_CONTENT_LENGTH = 16 * 1_024
    ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH = 16 * 1_024
    DEVICE_AUTH_MAX_HEADER_LENGTH = 512
    DEVICE_AUTH_CLOCK_SKEW_SECONDS = 300
    DEVICE_AUTH_NONCE_TTL_SECONDS = 600
    ENROLLMENT_TOKEN_TTL_SECONDS = 600
    POLICY_SYNC_RATE_LIMIT = os.getenv("POLICY_SYNC_RATE_LIMIT") or "60 per minute"


class DevelopmentConfig(Config):
    DEBUG = _environment_flag("FLASK_DEBUG")
    DATABASE_ENV_VAR = "DEVELOPMENT_DATABASE_URL"
    REQUIRE_POOLED_DATABASE_URL = True
    SQLALCHEMY_ENGINE_OPTIONS = POSTGRES_ENGINE_OPTIONS
    LOG_LEVEL = "DEBUG" if DEBUG else "INFO"


class TestingConfig(Config):
    TESTING = True
    DATABASE_ENV_VAR = None
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    LOG_LEVEL = "WARNING"
    RATELIMIT_ENABLED = False
    PAIRING_TOKEN_PEPPER = "testing-pairing-token-pepper-value"
    POLICY_SYNC_AUDIT_KEY = "testing-policy-sync-audit-key-value"
    ENROLLMENT_ADMIN_ENABLED = True


class PostgresTestingConfig(Config):
    TESTING = True
    DATABASE_ENV_VAR = "POSTGRES_TEST_DATABASE_URL"
    SQLALCHEMY_ENGINE_OPTIONS = POSTGRES_ENGINE_OPTIONS
    LOG_LEVEL = "WARNING"
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    DATABASE_ENV_VAR = "PRODUCTION_DATABASE_URL"
    REQUIRE_POOLED_DATABASE_URL = True
    SQLALCHEMY_ENGINE_OPTIONS = POSTGRES_ENGINE_OPTIONS
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL")
    TRUSTED_PROXY_HOPS = 1


CONFIGURATIONS: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "postgres-testing": PostgresTestingConfig,
    "production": ProductionConfig,
}


def get_configuration(
    config_name: str | None = None,
) -> tuple[str, type[Config]]:
    environment_name = cast(str, os.getenv("APP_ENV", "development"))
    selected_name = (config_name or environment_name).lower()
    try:
        return selected_name, CONFIGURATIONS[selected_name]
    except KeyError as error:
        valid_names = ", ".join(sorted(CONFIGURATIONS))
        raise ValueError(
            f"Unknown application environment '{selected_name}'. "
            f"Expected one of: {valid_names}"
        ) from error


def resolve_database_uri(configuration: type[Config]) -> str | None:
    if configuration.DATABASE_ENV_VAR is None:
        return configuration.SQLALCHEMY_DATABASE_URI

    database_uri = os.getenv(configuration.DATABASE_ENV_VAR)
    if not database_uri:
        return None
    normalized_uri = _normalize_database_uri(database_uri)
    _validate_neon_database_uri(
        configuration.DATABASE_ENV_VAR,
        normalized_uri,
        require_pooled=configuration.REQUIRE_POOLED_DATABASE_URL,
    )
    return normalized_uri


def resolve_migration_database_uri(
    app_environment: str,
    application_database_uri: str | None,
) -> str | None:
    if app_environment == "testing":
        return application_database_uri

    database_uri = os.getenv("MIGRATION_DATABASE_URL")
    if not database_uri:
        return None

    normalized_uri = _normalize_database_uri(database_uri)
    _validate_neon_database_uri(
        "MIGRATION_DATABASE_URL",
        normalized_uri,
        require_direct=True,
    )
    return normalized_uri


def validate_database_separation() -> None:
    branch_variables: dict[str, str] = {}

    for variable_name, require_pooled in APPLICATION_DATABASE_ENVIRONMENTS:
        database_uri = os.getenv(variable_name)
        if not database_uri:
            continue

        normalized_uri = _normalize_database_uri(database_uri)
        parsed_url = _validate_neon_database_uri(
            variable_name,
            normalized_uri,
            require_pooled=require_pooled,
        )
        branch_identity = _neon_branch_identity(parsed_url)
        existing_variable = branch_variables.get(branch_identity)
        if existing_variable is not None:
            raise RuntimeError(
                "Configured application databases must use separate Neon branches"
            )
        branch_variables[branch_identity] = variable_name


def validate_migration_target(
    application_database_uri: str,
    migration_database_uri: str,
) -> None:
    application_url = _validate_neon_database_uri(
        "active application database URL",
        application_database_uri,
    )
    migration_url = _validate_neon_database_uri(
        "MIGRATION_DATABASE_URL",
        migration_database_uri,
        require_direct=True,
    )
    if _neon_branch_identity(application_url) != _neon_branch_identity(migration_url):
        raise RuntimeError(
            "MIGRATION_DATABASE_URL must target the active application branch"
        )


def _validate_neon_database_uri(
    variable_name: str,
    database_uri: str,
    *,
    require_pooled: bool = False,
    require_direct: bool = False,
) -> URL:
    try:
        parsed_url = make_url(database_uri)
    except ArgumentError as error:
        raise RuntimeError(
            f"{variable_name} must contain a valid PostgreSQL URL"
        ) from error

    if parsed_url.drivername not in {
        "postgresql",
        "postgresql+psycopg2",
    }:
        raise RuntimeError(f"{variable_name} must contain a PostgreSQL URL")

    hostname = (parsed_url.host or "").lower()
    if not hostname.endswith(NEON_HOST_SUFFIX):
        raise RuntimeError(f"{variable_name} must target Neon PostgreSQL")

    ssl_mode = parsed_url.query.get("sslmode")
    if ssl_mode not in SECURE_POSTGRES_SSL_MODES:
        raise RuntimeError(f"{variable_name} must require PostgreSQL TLS")

    is_pooled = hostname.split(".", maxsplit=1)[0].endswith("-pooler")
    if require_pooled and not is_pooled:
        raise RuntimeError(f"{variable_name} must use a pooled Neon connection")
    if require_direct and is_pooled:
        raise RuntimeError(f"{variable_name} must use a direct Neon connection")

    return parsed_url


def _neon_branch_identity(database_url: URL) -> str:
    hostname = (database_url.host or "").lower()
    endpoint_name, separator, remainder = hostname.partition(".")
    if endpoint_name.endswith("-pooler"):
        endpoint_name = endpoint_name.removesuffix("-pooler")
    return f"{endpoint_name}{separator}{remainder}"


__all__ = [
    "Config",
    "DevelopmentConfig",
    "PostgresTestingConfig",
    "ProductionConfig",
    "TestingConfig",
    "get_configuration",
    "resolve_database_uri",
    "resolve_migration_database_uri",
    "validate_database_separation",
    "validate_migration_target",
]
