import json
from unittest.mock import Mock

import pytest
from flask import Flask

from app import create_app
from app.extensions import limiter

DEVELOPMENT_URL = (
    "postgresql://ep-development-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
)
PRODUCTION_URL = (
    "postgresql://ep-production-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
)
DATABASE_VARIABLES = (
    "DEVELOPMENT_DATABASE_URL",
    "POSTGRES_TEST_DATABASE_URL",
    "PRODUCTION_DATABASE_URL",
    "MIGRATION_DATABASE_URL",
)


@pytest.fixture(autouse=True)
def clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable_name in DATABASE_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_nonproduction_startup_generates_distinct_ephemeral_secrets() -> None:
    application = create_app(
        "testing",
        {
            "SECRET_KEY": None,
            "JWT_SECRET_KEY": None,
            "ADMIN_AUDIT_PSEUDONYM_KEY": None,
            "POLICY_SYNC_AUDIT_KEY": None,
        },
    )

    assert isinstance(application.config["SECRET_KEY"], str)
    assert len(application.config["SECRET_KEY"]) >= 32
    assert isinstance(application.config["JWT_SECRET_KEY"], str)
    assert len(application.config["JWT_SECRET_KEY"]) >= 32
    assert application.config["SECRET_KEY"] != application.config["JWT_SECRET_KEY"]
    assert isinstance(application.config["ADMIN_AUDIT_PSEUDONYM_KEY"], str)
    assert len(application.config["ADMIN_AUDIT_PSEUDONYM_KEY"]) >= 32
    assert isinstance(application.config["POLICY_SYNC_AUDIT_KEY"], str)
    assert len(application.config["POLICY_SYNC_AUDIT_KEY"]) >= 32
    assert (
        len(
            {
                application.config["SECRET_KEY"],
                application.config["JWT_SECRET_KEY"],
                application.config["ADMIN_AUDIT_PSEUDONYM_KEY"],
                application.config["POLICY_SYNC_AUDIT_KEY"],
            }
        )
        == 4
    )
    assert application.config["DEBUG"] is False
    assert application.config["RATELIMIT_ENABLED"] is False


def test_limiter_is_initialized_without_default_route_limits() -> None:
    application = create_app("testing", {"RATELIMIT_ENABLED": True})

    assert limiter in application.extensions["limiter"]
    assert application.config["RATELIMIT_DEFAULT"] == []
    assert application.config["RATELIMIT_ENABLED"] is True


@pytest.mark.parametrize(
    ("secret_key", "jwt_secret_key", "audit_key", "expected_message"),
    [
        ("short", "j" * 32, "a" * 32, "at least 32"),
        ("f" * 32, "short", "a" * 32, "at least 32"),
        ("f" * 32, "j" * 32, "short", "at least 32"),
        ("s" * 32, "s" * 32, "a" * 32, "distinct"),
        ("f" * 32, "a" * 32, "a" * 32, "distinct"),
    ],
)
def test_production_rejects_unsafe_secrets(
    monkeypatch: pytest.MonkeyPatch,
    secret_key: str,
    jwt_secret_key: str,
    audit_key: str,
    expected_message: str,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", PRODUCTION_URL)

    with pytest.raises(RuntimeError, match=expected_message):
        create_app(
            "production",
            {
                "SECRET_KEY": secret_key,
                "JWT_SECRET_KEY": jwt_secret_key,
                "ADMIN_AUDIT_PSEUDONYM_KEY": audit_key,
                "POLICY_SYNC_AUDIT_KEY": "p" * 32,
            },
        )


def test_production_starts_with_distinct_strong_secrets(
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

    assert application.config["DEBUG"] is False
    assert application.config["TESTING"] is False


@pytest.mark.parametrize("sync_audit_key", ["short", "a" * 32])
def test_production_rejects_unsafe_policy_sync_audit_key(
    monkeypatch: pytest.MonkeyPatch,
    sync_audit_key: str,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", PRODUCTION_URL)
    with pytest.raises(RuntimeError, match="at least 32|distinct"):
        create_app(
            "production",
            {
                "SECRET_KEY": "f" * 32,
                "JWT_SECRET_KEY": "j" * 32,
                "ADMIN_AUDIT_PSEUDONYM_KEY": "a" * 32,
                "POLICY_SYNC_AUDIT_KEY": sync_audit_key,
            },
        )


@pytest.mark.parametrize("unsafe_mode", ["DEBUG", "TESTING"])
def test_production_rejects_debug_or_testing_mode(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_mode: str,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", PRODUCTION_URL)

    with pytest.raises(RuntimeError, match="debug or testing"):
        create_app(
            "production",
            {
                "SECRET_KEY": "f" * 32,
                "JWT_SECRET_KEY": "j" * 32,
                "ADMIN_AUDIT_PSEUDONYM_KEY": "a" * 32,
                "POLICY_SYNC_AUDIT_KEY": "p" * 32,
                unsafe_mode: True,
            },
        )


def test_sentry_stays_inactive_without_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentry_init = Mock()
    monkeypatch.setattr("app.observability.sentry_sdk.init", sentry_init)

    application = create_app("testing", {"SENTRY_DSN": None})

    sentry_init.assert_not_called()
    assert application.extensions["sentry"]["enabled"] is False


def test_sentry_stays_inactive_in_test_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentry_init = Mock()
    monkeypatch.setattr("app.observability.sentry_sdk.init", sentry_init)

    application = create_app(
        "testing",
        {"SENTRY_DSN": "https://public@example.invalid/1"},
    )

    sentry_init.assert_not_called()
    assert application.extensions["sentry"] == {
        "enabled": False,
        "environment": "test",
    }


def test_enabled_sentry_is_conservative_and_scrubs_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVELOPMENT_DATABASE_URL", DEVELOPMENT_URL)
    sentry_init = Mock()
    monkeypatch.setattr("app.observability.sentry_sdk.init", sentry_init)
    secret_key = "development-secret-value-that-must-be-redacted"

    application = create_app(
        "development",
        {
            "SECRET_KEY": secret_key,
            "SENTRY_DSN": "https://public@example.invalid/1",
        },
    )

    sentry_init.assert_called_once()
    options = sentry_init.call_args.kwargs
    assert options["environment"] == "development"
    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["sample_rate"] <= 0.25
    assert options["traces_sample_rate"] <= 0.05
    event = {
        "message": f"failure with {secret_key}",
        "request": {"data": secret_key},
        "extra": {"authorization": "Bearer private-token"},
    }

    scrubbed_event = options["before_send"](event, {})

    assert "request" not in scrubbed_event
    assert secret_key not in repr(scrubbed_event)
    assert "private-token" not in repr(scrubbed_event)
    assert application.extensions["sentry"] == {
        "enabled": True,
        "environment": "development",
    }


def test_enabled_sentry_labels_production_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", PRODUCTION_URL)
    sentry_init = Mock()
    monkeypatch.setattr("app.observability.sentry_sdk.init", sentry_init)

    application = create_app(
        "production",
        {
            "SECRET_KEY": "f" * 32,
            "JWT_SECRET_KEY": "j" * 32,
            "ADMIN_AUDIT_PSEUDONYM_KEY": "a" * 32,
            "POLICY_SYNC_AUDIT_KEY": "p" * 32,
            "SENTRY_DSN": "https://public@example.invalid/1",
        },
    )

    assert sentry_init.call_args.kwargs["environment"] == "production"
    assert application.extensions["sentry"] == {
        "enabled": True,
        "environment": "production",
    }


def test_structured_logging_redacts_secrets_and_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_key = "structured-log-secret-value"
    audit_key = "structured-log-audit-pseudonym-key-value"
    sync_audit_key = "structured-log-policy-sync-audit-key-value"
    database_url = "postgresql://test-user:test-password@example.invalid/db"
    application: Flask = create_app(
        "testing",
        {
            "SECRET_KEY": secret_key,
            "JWT_SECRET_KEY": "structured-log-jwt-secret-value",
            "ADMIN_AUDIT_PSEUDONYM_KEY": audit_key,
            "POLICY_SYNC_AUDIT_KEY": sync_audit_key,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
        },
    )

    application.logger.error(
        "Startup failure secret=%s database=%s",
        f"{secret_key} audit={audit_key} sync_audit={sync_audit_key}",
        database_url,
        extra={"event": "startup_test"},
    )
    captured = capsys.readouterr()
    log_record = json.loads(captured.err.strip().splitlines()[-1])

    assert log_record["environment"] == "test"
    assert log_record["level"] == "ERROR"
    assert log_record["event"] == "startup_test"
    assert secret_key not in captured.err
    assert audit_key not in captured.err
    assert sync_audit_key not in captured.err
    assert "test-password" not in captured.err
    assert "<redacted>" in captured.err


def test_enrollment_enforcement_requires_pairing_pepper() -> None:
    with pytest.raises(RuntimeError, match="PAIRING_TOKEN_PEPPER"):
        create_app(
            "testing",
            {
                "DEVICE_ENROLLMENT_MODE": "all_required",
                "PAIRING_TOKEN_PEPPER": None,
            },
        )


def test_unknown_enrollment_mode_fails_startup() -> None:
    with pytest.raises(RuntimeError, match="DEVICE_ENROLLMENT_MODE"):
        create_app(
            "testing",
            {"DEVICE_ENROLLMENT_MODE": "unsafe_fallback"},
        )
