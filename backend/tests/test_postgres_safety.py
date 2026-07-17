import pytest

from test_support.postgres_safety import (
    APPROVED_POSTGRES_TEST_BRANCH,
    PostgresTestSafetyError,
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)


APPLICATION_URL = (
    "postgresql://ep-integration-pooler.us-east-2.aws.neon.tech/"
    "neondb?sslmode=require"
)
MIGRATION_URL = (
    "postgresql://ep-integration.us-east-2.aws.neon.tech/"
    "neondb?sslmode=require"
)
DEVELOPMENT_URL = (
    "postgresql://ep-development-pooler.us-east-2.aws.neon.tech/"
    "neondb?sslmode=require"
)
PRODUCTION_URL = (
    "postgresql://ep-production-pooler.us-east-2.aws.neon.tech/"
    "neondb?sslmode=require"
)


def safe_environment(**overrides: str) -> dict[str, str]:
    environment = {
        "POSTGRES_TEST_BRANCH_NAME": APPROVED_POSTGRES_TEST_BRANCH,
        "POSTGRES_TEST_DATABASE_URL": APPLICATION_URL,
        "MIGRATION_DATABASE_URL": MIGRATION_URL,
        "ALLOW_DESTRUCTIVE_POSTGRES_TESTS": "false",
        "DEVELOPMENT_DATABASE_URL": DEVELOPMENT_URL,
        "PRODUCTION_DATABASE_URL": PRODUCTION_URL,
    }
    environment.update(overrides)
    return environment


def test_guard_accepts_separated_pooled_and_direct_test_urls() -> None:
    approved = validate_postgres_test_environment(
        safe_environment(),
        require_migration=True,
    )

    assert approved.branch_name == APPROVED_POSTGRES_TEST_BRANCH
    assert approved.destructive_allowed is False
    assert "postgresql" not in repr(approved)


@pytest.mark.parametrize(
    ("overrides", "require_migration", "expected_name"),
    [
        (
            {"POSTGRES_TEST_DATABASE_URL": ""},
            False,
            "POSTGRES_TEST_DATABASE_URL",
        ),
        ({"MIGRATION_DATABASE_URL": ""}, True, "MIGRATION_DATABASE_URL"),
        (
            {"POSTGRES_TEST_DATABASE_URL": "sqlite:///:memory:"},
            False,
            "POSTGRES_TEST_DATABASE_URL",
        ),
        (
            {
                "POSTGRES_TEST_DATABASE_URL": (
                    "postgresql://ep-integration.us-east-2.aws.neon.tech/"
                    "neondb?sslmode=require"
                )
            },
            False,
            "POSTGRES_TEST_DATABASE_URL",
        ),
        (
            {"MIGRATION_DATABASE_URL": APPLICATION_URL},
            True,
            "MIGRATION_DATABASE_URL",
        ),
        (
            {
                "MIGRATION_DATABASE_URL": (
                    "postgresql://ep-other.us-east-2.aws.neon.tech/"
                    "neondb?sslmode=require"
                )
            },
            True,
            "same dedicated Neon test branch",
        ),
        (
            {
                "POSTGRES_TEST_DATABASE_URL": (
                    "postgresql://ep-integration-pooler.us-east-2.aws.neon.tech/"
                    "neondb"
                )
            },
            False,
            "TLS",
        ),
        ({"POSTGRES_TEST_BRANCH_NAME": ""}, False, "POSTGRES_TEST_BRANCH_NAME"),
        (
            {"POSTGRES_TEST_BRANCH_NAME": "development"},
            False,
            "POSTGRES_TEST_BRANCH_NAME",
        ),
        (
            {"POSTGRES_TEST_BRANCH_NAME": "another-test-branch"},
            False,
            "POSTGRES_TEST_BRANCH_NAME",
        ),
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
def test_guard_rejects_a_protected_branch_even_with_pooling_difference(
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


@pytest.mark.parametrize(
    "missing_variable",
    ["MIGRATION_DATABASE_URL"],
)
def test_destructive_guard_requires_direct_migration_target(
    missing_variable: str,
) -> None:
    environment = safe_environment(
        ALLOW_DESTRUCTIVE_POSTGRES_TESTS="true"
    )
    environment.pop(missing_variable)

    with pytest.raises(PostgresTestSafetyError, match=missing_variable):
        validate_postgres_test_environment(
            environment,
            require_destructive=True,
        )


def test_guard_errors_and_result_never_disclose_credentials() -> None:
    username = "placeholder-user"
    password = "placeholder-password"
    credential_url = APPLICATION_URL.replace(
        "postgresql://",
        f"postgresql://{username}:{password}@",
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


class FakeConnectionInfo:
    def __init__(
        self,
        *,
        host: str = "ep-integration-pooler.us-east-2.aws.neon.tech",
        dbname: str = "neondb",
        ssl_in_use: bool = True,
    ) -> None:
        self.host = host
        self.dbname = dbname
        self.ssl_in_use = ssl_in_use


class FakeConnection:
    def __init__(self, info: FakeConnectionInfo) -> None:
        self.info = info


def test_connected_guard_accepts_exact_endpoint_database_and_tls() -> None:
    approved = validate_postgres_test_environment(safe_environment())

    validate_connected_postgres_test_environment(
        FakeConnection(FakeConnectionInfo()),
        approved,
    )


@pytest.mark.parametrize(
    ("connection_info", "expected_message"),
    [
        (
            FakeConnectionInfo(
                host="ep-development-pooler.us-east-2.aws.neon.tech"
            ),
            "endpoint",
        ),
        (FakeConnectionInfo(dbname="other_database"), "database"),
        (FakeConnectionInfo(ssl_in_use=False), "TLS"),
    ],
)
def test_connected_guard_fails_closed_for_wrong_live_identity(
    connection_info: FakeConnectionInfo,
    expected_message: str,
) -> None:
    approved = validate_postgres_test_environment(safe_environment())

    with pytest.raises(PostgresTestSafetyError, match=expected_message):
        validate_connected_postgres_test_environment(
            FakeConnection(connection_info),
            approved,
        )
