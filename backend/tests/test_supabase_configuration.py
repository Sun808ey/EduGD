from types import SimpleNamespace

import pytest

from app.config import (
    ProductionConfig,
    database_project_identity,
    resolve_database_uri,
    resolve_migration_database_uri,
    validate_database_separation,
    validate_migration_target,
    validate_postgres_database_uri,
)
from test_support.postgres_safety import (
    PostgresTestSafetyError,
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

PROJECT = "abcdefghijklmnopqrst"
DIRECT = f"postgresql://runtime:placeholder@db.{PROJECT}.supabase.co/postgres?sslmode=verify-full"
SESSION = f"postgresql://runtime.{PROJECT}:placeholder@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=verify-full"


@pytest.fixture(autouse=True)
def clear_database_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "DEVELOPMENT_DATABASE_URL",
        "PRODUCTION_DATABASE_URL",
        "POSTGRES_TEST_DATABASE_URL",
        "MIGRATION_DATABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("url", [DIRECT, SESSION])
def test_runtime_and_migration_support_persistent_supabase_connections(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", url)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", url)
    assert resolve_database_uri(ProductionConfig) == url
    assert resolve_migration_database_uri("production", url) == url
    validate_migration_target(url, DIRECT)
    validate_migration_target(url, SESSION)


@pytest.mark.parametrize(
    "url",
    [
        SESSION.replace(":5432", ":6543"),
        DIRECT.replace("verify-full", "require"),
        DIRECT.replace("verify-full", "disable"),
        DIRECT.replace(PROJECT, "invalid"),
        SESSION.replace(f"runtime.{PROJECT}", "runtime"),
        DIRECT.replace("runtime:placeholder@", ""),
        DIRECT.replace("/postgres?", "/?"),
        DIRECT + "&host=example.org",
        DIRECT + "&hostaddr=127.0.0.1",
        DIRECT + "&dbname=other",
        DIRECT + "&user=other",
        DIRECT + "&options=-csearch_path=other",
        DIRECT + "&service=other",
        DIRECT + "&sslmode=disable",
        DIRECT.replace(".co/", ".co:bad/"),
        "postgresql://private:placeholder@[",
        "sqlite:///db",
        DIRECT.replace("db.", "other."),
    ],
)
def test_unsafe_supabase_urls_fail_without_credentials(url: str) -> None:
    with pytest.raises(RuntimeError) as error:
        validate_postgres_database_uri("PRODUCTION_DATABASE_URL", url)
    assert "placeholder" not in str(error.value)
    assert error.value.__cause__ is None


def test_tls_certificate_path_is_preserved() -> None:
    parsed = validate_postgres_database_uri("URL", DIRECT + "&sslrootcert=/run/ca.pem")
    assert parsed.query["sslrootcert"] == "/run/ca.pem"


def test_project_and_database_must_match() -> None:
    for migration_url in (
        SESSION.replace(PROJECT, "zyxwvutsrqponmlkjihg"),
        DIRECT.replace("/postgres?", "/other?"),
    ):
        with pytest.raises(RuntimeError, match="MIGRATION_DATABASE_URL"):
            validate_migration_target(DIRECT, migration_url)


def test_database_separation_recognizes_pooler_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", DIRECT)
    monkeypatch.setenv("POSTGRES_TEST_DATABASE_URL", SESSION)
    with pytest.raises(RuntimeError, match="separate"):
        validate_database_separation()
    monkeypatch.setenv(
        "POSTGRES_TEST_DATABASE_URL", SESSION.replace(PROJECT, "zyxwvutsrqponmlkjihg")
    )
    validate_database_separation()


def environment() -> dict[str, str]:
    return {
        "POSTGRES_TEST_BRANCH_NAME": "backend-integration-test",
        "POSTGRES_TEST_PROJECT_REF": PROJECT,
        "POSTGRES_TEST_DATABASE_URL": SESSION,
        "MIGRATION_DATABASE_URL": DIRECT,
        "ALLOW_DESTRUCTIVE_POSTGRES_TESTS": "true",
    }


def test_supabase_test_guard_checks_live_pooler_tenant() -> None:
    approved = validate_postgres_test_environment(
        environment(), require_destructive=True
    )
    assert approved.project_ref == PROJECT
    info = SimpleNamespace(
        host="aws-0-eu-west-1.pooler.supabase.com",
        user=f"runtime.{PROJECT}",
        port=5432,
        dbname="postgres",
        ssl_in_use=True,
    )
    validate_connected_postgres_test_environment(SimpleNamespace(info=info), approved)
    for field, value in (
        ("user", "runtime.other"),
        ("host", "other"),
        ("port", 6543),
        ("dbname", "other"),
        ("ssl_in_use", False),
    ):
        invalid = SimpleNamespace(**vars(info))
        setattr(invalid, field, value)
        with pytest.raises(PostgresTestSafetyError):
            validate_connected_postgres_test_environment(
                SimpleNamespace(info=invalid), approved
            )


@pytest.mark.parametrize(
    "name,value",
    [
        ("POSTGRES_TEST_PROJECT_REF", ""),
        ("POSTGRES_TEST_PROJECT_REF", "zyxwvutsrqponmlkjihg"),
        ("ALLOW_DESTRUCTIVE_POSTGRES_TESTS", "false"),
        ("MIGRATION_DATABASE_URL", ""),
        ("MIGRATION_DATABASE_URL", DIRECT.replace("/postgres?", "/other?")),
        ("MIGRATION_DATABASE_URL", DIRECT.replace(PROJECT, "zyxwvutsrqponmlkjihg")),
        ("PRODUCTION_DATABASE_URL", DIRECT),
        ("DEVELOPMENT_DATABASE_URL", SESSION),
    ],
)
def test_supabase_guard_rejects_unapproved_targets(name: str, value: str) -> None:
    values = environment()
    values[name] = value
    with pytest.raises(PostgresTestSafetyError):
        validate_postgres_test_environment(values, require_destructive=True)


def test_project_identity_is_provider_qualified() -> None:
    assert (
        database_project_identity(validate_postgres_database_uri("URL", SESSION))
        == f"supabase:{PROJECT}"
    )
