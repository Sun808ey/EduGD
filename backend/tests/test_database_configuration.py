import pytest

from app import create_app
from app.config import (
    DevelopmentConfig,
    PostgresTestingConfig,
    ProductionConfig,
    TestingConfig,
    resolve_database_uri,
    resolve_migration_database_uri,
    validate_database_separation,
)

DEVELOPMENT_URL = (
    "postgresql://ep-development-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
)
TEST_URL = "postgresql://ep-integration.us-east-2.aws.neon.tech/neondb?sslmode=require"
PRODUCTION_URL = (
    "postgresql://ep-production-pooler.us-east-2.aws.neon.tech/"
    "neondb?sslmode=verify-full"
)
MIGRATION_URL = (
    "postgresql://ep-development.us-east-2.aws.neon.tech/neondb?sslmode=require"
)
DATABASE_VARIABLES = (
    "DATABASE_URL",
    "DEVELOPMENT_DATABASE_URL",
    "POSTGRES_TEST_DATABASE_URL",
    "PRODUCTION_DATABASE_URL",
    "MIGRATION_DATABASE_URL",
)


@pytest.fixture(autouse=True)
def clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable_name in DATABASE_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


@pytest.mark.parametrize(
    ("configuration", "variable_name", "database_url"),
    [
        (DevelopmentConfig, "DEVELOPMENT_DATABASE_URL", DEVELOPMENT_URL),
        (PostgresTestingConfig, "POSTGRES_TEST_DATABASE_URL", TEST_URL),
        (ProductionConfig, "PRODUCTION_DATABASE_URL", PRODUCTION_URL),
    ],
)
def test_environment_uses_its_own_database_variable(
    monkeypatch: pytest.MonkeyPatch,
    configuration: type[DevelopmentConfig],
    variable_name: str,
    database_url: str,
) -> None:
    monkeypatch.setenv(variable_name, database_url)

    assert resolve_database_uri(configuration) == database_url


def test_development_normalizes_legacy_postgres_scheme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = DEVELOPMENT_URL.replace("postgresql://", "postgres://")
    monkeypatch.setenv("DEVELOPMENT_DATABASE_URL", database_url)

    resolved_url = resolve_database_uri(DevelopmentConfig)

    assert resolved_url is not None
    assert resolved_url.startswith("postgresql+psycopg2://")


def test_legacy_database_url_is_not_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DEVELOPMENT_URL)

    with pytest.raises(RuntimeError, match="DEVELOPMENT_DATABASE_URL"):
        create_app("development")


@pytest.mark.parametrize(
    ("config_name", "variable_name"),
    [
        ("development", "DEVELOPMENT_DATABASE_URL"),
        ("postgres-testing", "POSTGRES_TEST_DATABASE_URL"),
        ("production", "PRODUCTION_DATABASE_URL"),
    ],
)
def test_missing_environment_database_fails_closed(
    config_name: str,
    variable_name: str,
) -> None:
    with pytest.raises(RuntimeError, match=variable_name):
        create_app(config_name)


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///development.db",
        ("postgresql://ep-development-pooler.example.com/neondb?sslmode=require"),
        ("postgresql://ep-development-pooler.us-east-2.aws.neon.tech/neondb"),
        ("postgresql://ep-development.us-east-2.aws.neon.tech/neondb?sslmode=require"),
    ],
)
def test_development_rejects_unsafe_or_non_pooled_database_url(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    monkeypatch.setenv("DEVELOPMENT_DATABASE_URL", database_url)

    with pytest.raises(RuntimeError) as error:
        resolve_database_uri(DevelopmentConfig)

    assert "DEVELOPMENT_DATABASE_URL" in str(error.value)
    assert database_url not in str(error.value)


def test_postgres_testing_accepts_direct_neon_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_TEST_DATABASE_URL", TEST_URL)

    assert resolve_database_uri(PostgresTestingConfig) == TEST_URL


def test_migrations_require_direct_neon_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIGRATION_DATABASE_URL", DEVELOPMENT_URL)

    with pytest.raises(RuntimeError, match="MIGRATION_DATABASE_URL"):
        resolve_migration_database_uri("development", None)

    monkeypatch.setenv("MIGRATION_DATABASE_URL", MIGRATION_URL)

    assert resolve_migration_database_uri("development", None) == MIGRATION_URL


def test_sqlite_unit_tests_reuse_the_application_database_for_migrations() -> None:
    application_url = TestingConfig.SQLALCHEMY_DATABASE_URI

    assert resolve_migration_database_uri("testing", application_url) == application_url


def test_configured_application_databases_must_use_separate_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVELOPMENT_DATABASE_URL", DEVELOPMENT_URL)
    reused_test_url = DEVELOPMENT_URL.replace("-pooler", "")
    monkeypatch.setenv("POSTGRES_TEST_DATABASE_URL", reused_test_url)

    with pytest.raises(RuntimeError, match="separate Neon branches"):
        validate_database_separation()


def test_separate_neon_branches_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVELOPMENT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("POSTGRES_TEST_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", PRODUCTION_URL)

    validate_database_separation()


def test_postgres_environments_use_bounded_resilient_connections() -> None:
    bounded_postgres_options = {
        "connect_args": {"connect_timeout": 3},
        "pool_pre_ping": True,
        "pool_timeout": 3,
    }
    assert DevelopmentConfig.SQLALCHEMY_ENGINE_OPTIONS == bounded_postgres_options
    assert PostgresTestingConfig.SQLALCHEMY_ENGINE_OPTIONS == bounded_postgres_options
    assert ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS == bounded_postgres_options
    assert TestingConfig.SQLALCHEMY_ENGINE_OPTIONS == {}
    assert DevelopmentConfig.READINESS_STATEMENT_TIMEOUT_MS == 2_000
    assert PostgresTestingConfig.READINESS_STATEMENT_TIMEOUT_MS == 2_000
    assert ProductionConfig.READINESS_STATEMENT_TIMEOUT_MS == 2_000


def test_production_fails_closed_without_required_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", PRODUCTION_URL)

    with pytest.raises(RuntimeError, match="production secrets"):
        create_app("production")


def test_production_starts_with_database_and_required_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", PRODUCTION_URL)

    application = create_app(
        "production",
        {
            "SECRET_KEY": "f" * 32,
            "JWT_SECRET_KEY": "j" * 32,
            "ADMIN_AUDIT_PSEUDONYM_KEY": "a" * 32,
            "POLICY_SYNC_AUDIT_KEY": "p" * 32,
        },
    )

    assert application.config["SQLALCHEMY_DATABASE_URI"] == PRODUCTION_URL
    assert application.config["MIGRATION_DATABASE_URI"] is None


def test_application_keeps_direct_migration_url_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVELOPMENT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", MIGRATION_URL)

    application = create_app("development")

    assert application.config["SQLALCHEMY_DATABASE_URI"] == DEVELOPMENT_URL
    assert application.config["MIGRATION_DATABASE_URI"] == MIGRATION_URL


def test_migration_url_must_target_the_active_application_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVELOPMENT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL",
        TEST_URL,
    )

    with pytest.raises(RuntimeError, match="active application branch"):
        create_app("development")
