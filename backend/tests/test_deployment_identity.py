import runpy
from pathlib import Path

import pytest

from app.deployment_identity import RESOURCES, validate_deployment_identity


def deployment_values(environment: str) -> dict[str, str]:
    project, host, port, origin, railway_id = RESOURCES[environment]
    return {
        "EDUG_ENVIRONMENT": environment,
        "APP_ENV": "production",
        "RAILWAY_ENVIRONMENT_ID": railway_id,
        "PRODUCTION_DATABASE_URL": (
            f"postgresql://runtime:synthetic@db.{project}.supabase.co:5432/postgres"
            "?sslmode=verify-full"
        ),
        "REDIS_URL": f"rediss://default:synthetic@{host}:{port}/0",
        "ADMIN_FRONTEND_ORIGINS": origin,
    }


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_matching_deployment_identity(environment: str) -> None:
    validate_deployment_identity(deployment_values(environment))


@pytest.mark.parametrize(
    "name",
    [
        "PRODUCTION_DATABASE_URL",
        "REDIS_URL",
        "ADMIN_FRONTEND_ORIGINS",
        "RAILWAY_ENVIRONMENT_ID",
    ],
)
def test_cross_environment_value_rejected(name: str) -> None:
    values = deployment_values("staging")
    values[name] = deployment_values("production")[name]
    with pytest.raises(RuntimeError):
        validate_deployment_identity(values)


@pytest.mark.parametrize(
    "override",
    [
        {"EDUG_ENVIRONMENT": ""},
        {"APP_ENV": "development"},
        {"RAILWAY_ENVIRONMENT_ID": ""},
        {"POSTGRES_TEST_DATABASE_URL": "must-not-be-present"},
        {"REDIS_URL": "rediss://default:private@["},
    ],
)
def test_invalid_deployment_rejected_without_secret_output(
    override: dict[str, str],
) -> None:
    values = deployment_values("staging") | override
    with pytest.raises(RuntimeError) as error:
        validate_deployment_identity(values)
    assert "private" not in str(error.value)


def test_cross_environment_migration_url_rejected() -> None:
    values = deployment_values("staging")
    values["MIGRATION_DATABASE_URL"] = deployment_values("production")[
        "PRODUCTION_DATABASE_URL"
    ]
    with pytest.raises(RuntimeError, match="Migration database"):
        validate_deployment_identity(values)


def test_migration_url_for_different_database_is_rejected() -> None:
    values = deployment_values("production")
    values["MIGRATION_DATABASE_URL"] = values["PRODUCTION_DATABASE_URL"].replace(
        "/postgres?", "/separate_database?"
    )
    with pytest.raises(RuntimeError, match="Migration database"):
        validate_deployment_identity(values)


def test_railway_entrypoint_cannot_fall_back_to_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("EDUG_ENVIRONMENT", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", RESOURCES["staging"][4])
    with pytest.raises(RuntimeError, match="EDUG_ENVIRONMENT"):
        runpy.run_path(str(Path(__file__).resolve().parents[1] / "run.py"))
