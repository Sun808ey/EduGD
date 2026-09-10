from types import SimpleNamespace

import pytest

from test_support.postgres_safety import (
    APPROVED_POSTGRES_TEST_PURPOSE,
    PostgresTestSafetyError,
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

PROJECT = "abcdefghijklmnopqrst"
DEVELOPMENT_PROJECT = "bcdefghijklmnopqrstu"
PRODUCTION_PROJECT = "cdefghijklmnopqrstuv"
OTHER_PROJECT = "defghijklmnopqrstuvw"
APPLICATION_URL = (
    f"postgresql://runtime.{PROJECT}:placeholder@"
    "aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=verify-full"
)
MIGRATION_URL = (
    f"postgresql://migration:placeholder@db.{PROJECT}.supabase.co:5432/"
    "postgres?sslmode=verify-full"
)
DEVELOPMENT_URL = (
    f"postgresql://runtime:placeholder@db.{DEVELOPMENT_PROJECT}.supabase.co:5432/"
    "postgres?sslmode=verify-full"
)
PRODUCTION_URL = (
    f"postgresql://runtime:placeholder@db.{PRODUCTION_PROJECT}.supabase.co:5432/"
    "postgres?sslmode=verify-full"
)


def safe_environment(**overrides: str) -> dict[str, str]:
    environment = {
        "POSTGRES_TEST_PURPOSE": APPROVED_POSTGRES_TEST_PURPOSE,
        "POSTGRES_TEST_PROJECT_REF": PROJECT,
        "POSTGRES_TEST_DATABASE_URL": APPLICATION_URL,
        "MIGRATION_DATABASE_URL": MIGRATION_URL,
        "ALLOW_DESTRUCTIVE_POSTGRES_TESTS": "false",
        "DEVELOPMENT_DATABASE_URL": DEVELOPMENT_URL,
        "PRODUCTION_DATABASE_URL": PRODUCTION_URL,
    }
    environment.update(overrides)
    return environment


def test_guard_accepts_separated_session_and_direct_test_urls() -> None:
    approved = validate_postgres_test_environment(
        safe_environment(),
        require_migration=True,
    )

    assert approved.purpose == APPROVED_POSTGRES_TEST_PURPOSE
    assert approved.project_ref == PROJECT
    assert approved.destructive_allowed is False
    assert "postgresql" not in repr(approved)
    assert "placeholder" not in repr(approved)


@pytest.mark.parametrize(
    ("overrides", "require_migration", "expected_name"),
    [
        ({"POSTGRES_TEST_DATABASE_URL": ""}, False, "POSTGRES_TEST_DATABASE_URL"),
        ({"MIGRATION_DATABASE_URL": ""}, True, "MIGRATION_DATABASE_URL"),
        (
            {"POSTGRES_TEST_DATABASE_URL": "sqlite:///:memory:"},
            False,
            "POSTGRES_TEST_DATABASE_URL",
        ),
        (
            {
                "POSTGRES_TEST_DATABASE_URL": (
                    "postgresql://runtime:placeholder@db.example.invalid/postgres"
                    "?sslmode=verify-full"
                )
            },
            False,
            "Supabase project",
        ),
        (
            {
                "POSTGRES_TEST_DATABASE_URL": APPLICATION_URL.replace(
                    PROJECT, OTHER_PROJECT
                )
            },
            False,
            "POSTGRES_TEST_PROJECT_REF",
        ),
        (
            {"MIGRATION_DATABASE_URL": MIGRATION_URL.replace(PROJECT, OTHER_PROJECT)},
            True,
            "same dedicated Supabase project",
        ),
        (
            {"MIGRATION_DATABASE_URL": MIGRATION_URL.replace("/postgres?", "/other?")},
            True,
            "same dedicated Supabase project",
        ),
        (
            {
                "POSTGRES_TEST_DATABASE_URL": APPLICATION_URL.replace(
                    "verify-full", "require"
                )
            },
            False,
            "verify-full",
        ),
        ({"POSTGRES_TEST_PURPOSE": ""}, False, "POSTGRES_TEST_PURPOSE"),
        ({"POSTGRES_TEST_PURPOSE": "development"}, False, "POSTGRES_TEST_PURPOSE"),
        ({"POSTGRES_TEST_PROJECT_REF": ""}, False, "POSTGRES_TEST_PROJECT_REF"),
        ({"POSTGRES_TEST_PROJECT_REF": "invalid"}, False, "POSTGRES_TEST_PROJECT_REF"),
    ],
)
def test_guard_rejects_unsafe_configuration(
    overrides: dict[str, str],
    require_migration: bool,
    expected_name: str,
) -> None:
    with pytest.raises(PostgresTestSafetyError, match=expected_name):
        validate_postgres_test_environment(
            safe_environment(**overrides),
            require_migration=require_migration,
        )


@pytest.mark.parametrize(
    "protected_variable",
    ["DEVELOPMENT_DATABASE_URL", "PRODUCTION_DATABASE_URL"],
)
def test_guard_rejects_protected_project_reuse(
    protected_variable: str,
) -> None:
    environment = safe_environment()
    environment[protected_variable] = APPLICATION_URL

    with pytest.raises(PostgresTestSafetyError, match="separate"):
        validate_postgres_test_environment(environment)


def test_guard_requires_exact_destructive_opt_in() -> None:
    with pytest.raises(PostgresTestSafetyError, match="ALLOW_DESTRUCTIVE"):
        validate_postgres_test_environment(
            safe_environment(ALLOW_DESTRUCTIVE_POSTGRES_TESTS="TRUE"),
            require_destructive=True,
        )

    approved = validate_postgres_test_environment(
        safe_environment(ALLOW_DESTRUCTIVE_POSTGRES_TESTS="true"),
        require_destructive=True,
    )
    assert approved.destructive_allowed is True


def test_destructive_guard_requires_migration_target() -> None:
    environment = safe_environment(ALLOW_DESTRUCTIVE_POSTGRES_TESTS="true")
    environment.pop("MIGRATION_DATABASE_URL")

    with pytest.raises(PostgresTestSafetyError, match="MIGRATION_DATABASE_URL"):
        validate_postgres_test_environment(environment, require_destructive=True)


def test_guard_errors_and_result_never_disclose_credentials() -> None:
    username = f"placeholder-user.{PROJECT}"
    password = "placeholder-password"
    credential_url = APPLICATION_URL.replace(
        f"runtime.{PROJECT}:placeholder",
        f"{username}:{password}",
    )
    environment = safe_environment(
        POSTGRES_TEST_DATABASE_URL=credential_url,
        DEVELOPMENT_DATABASE_URL=credential_url,
    )

    with pytest.raises(PostgresTestSafetyError) as error:
        validate_postgres_test_environment(environment)

    message = str(error.value)
    assert username not in message
    assert password not in message

    approved = validate_postgres_test_environment(
        safe_environment(POSTGRES_TEST_DATABASE_URL=credential_url)
    )
    rendered = repr(approved)
    assert username not in rendered
    assert password not in rendered


def test_invalid_url_does_not_retain_a_parser_exception() -> None:
    username = "placeholder-user"
    password = "placeholder-password"
    malformed_url = f"postgresql://{username}:{password}@["

    with pytest.raises(PostgresTestSafetyError) as error:
        validate_postgres_test_environment(
            safe_environment(POSTGRES_TEST_DATABASE_URL=malformed_url)
        )

    assert error.value.__cause__ is None
    assert username not in str(error.value)
    assert password not in str(error.value)


def connection_info(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "host": "aws-0-eu-west-1.pooler.supabase.com",
        "user": f"runtime.{PROJECT}",
        "port": 5432,
        "dbname": "postgres",
        "ssl_in_use": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_connected_guard_accepts_exact_project_database_role_port_and_tls() -> None:
    approved = validate_postgres_test_environment(safe_environment())
    validate_connected_postgres_test_environment(
        SimpleNamespace(info=connection_info()),
        approved,
    )


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("host", "other.pooler.supabase.com", "endpoint"),
        ("user", f"other.{PROJECT}", "endpoint"),
        ("port", 6543, "endpoint"),
        ("dbname", "other_database", "database"),
        ("ssl_in_use", False, "TLS"),
    ],
)
def test_connected_guard_fails_closed_for_wrong_live_identity(
    field: str,
    value: object,
    expected_message: str,
) -> None:
    approved = validate_postgres_test_environment(safe_environment())
    info = connection_info(**{field: value})

    with pytest.raises(PostgresTestSafetyError, match=expected_message):
        validate_connected_postgres_test_environment(
            SimpleNamespace(info=info),
            approved,
        )


def test_connected_guard_rejects_expected_url_outside_approved_project() -> None:
    approved = validate_postgres_test_environment(safe_environment())
    with pytest.raises(PostgresTestSafetyError, match="outside"):
        validate_connected_postgres_test_environment(
            SimpleNamespace(info=connection_info()),
            approved,
            expected_database_url=MIGRATION_URL.replace(PROJECT, OTHER_PROJECT),
        )
