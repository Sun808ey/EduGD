from datetime import UTC, datetime, timedelta

import pytest
from click.testing import Result
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import (
    ADMINISTRATOR_PERMISSIONS,
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    AdministratorSession,
)
from app.services.administrator_authentication import (
    AdministratorDatabaseError,
    AdministratorOperationError,
    bootstrap_administrator,
)

BOOTSTRAP_PASSWORD = "OfflineSchool!2026"
RESET_PASSWORD = "ReplacementKey!2026"
OPERATOR = "trusted-host-operator"
REASON = "approved administrator recovery operation"


def _bootstrap_arguments() -> list[str]:
    return [
        "admin",
        "bootstrap",
        "--username",
        "enrollment.admin",
        "--display-name",
        "Enrollment Administrator",
        "--operator",
        OPERATOR,
        "--reason",
        "initial school administrator bootstrap",
    ]


def _invoke_bootstrap(app: Flask) -> Result:
    return app.test_cli_runner().invoke(
        args=_bootstrap_arguments(),
        input=f"{BOOTSTRAP_PASSWORD}\n{BOOTSTRAP_PASSWORD}\n",
    )


def _load_administrator() -> Administrator:
    return db.session.execute(
        select(Administrator).where(Administrator.username == "enrollment.admin")
    ).scalar_one()


def _add_active_session(administrator: Administrator, digest: bytes) -> None:
    now = datetime.now(UTC)
    db.session.add(
        AdministratorSession(
            administrator_id=administrator.id,
            jti_digest=digest,
            expires_at=now + timedelta(minutes=15),
        )
    )
    db.session.commit()


def test_cli_does_not_offer_password_command_line_option(app: Flask) -> None:
    result = app.test_cli_runner().invoke(args=["admin", "bootstrap", "--help"])

    assert result.exit_code == 0
    assert "--password" not in result.output


def test_bootstrap_creates_one_administrator_permissions_and_event(app: Flask) -> None:
    result = _invoke_bootstrap(app)

    assert result.exit_code == 0
    assert result.exception is None
    assert "Administrator bootstrap completed." in result.output
    assert BOOTSTRAP_PASSWORD not in result.output

    with app.app_context():
        administrator = _load_administrator()
        permissions = db.session.execute(
            select(AdministratorPermission.permission).where(
                AdministratorPermission.administrator_id == administrator.id
            )
        ).scalars()
        event = db.session.execute(
            select(AdministratorAuthenticationEvent)
        ).scalar_one()

        assert administrator.status == "active"
        assert check_password_hash(
            administrator.password_verifier,
            BOOTSTRAP_PASSWORD,
        )
        assert set(permissions) == ADMINISTRATOR_PERMISSIONS
        assert event.category == "bootstrap"
        assert event.administrator_id == administrator.id
        assert event.trusted_operator_subject == OPERATOR
        assert "password" not in AdministratorAuthenticationEvent.__table__.c


def test_bootstrap_refuses_second_administrator(app: Flask) -> None:
    first_result = _invoke_bootstrap(app)
    second_result = app.test_cli_runner().invoke(
        args=[
            *_bootstrap_arguments(),
            "--username",
            "second.admin",
        ],
        input=f"{RESET_PASSWORD}\n{RESET_PASSWORD}\n",
    )

    assert first_result.exit_code == 0
    assert second_result.exit_code == 1
    assert "bootstrap has already been completed" in second_result.output
    assert RESET_PASSWORD not in second_result.output

    with app.app_context():
        count = db.session.scalar(select(func.count()).select_from(Administrator))
        assert count == 1


def test_reset_password_unlocks_and_revokes_active_sessions(app: Flask) -> None:
    assert _invoke_bootstrap(app).exit_code == 0
    with app.app_context():
        administrator = _load_administrator()
        _add_active_session(administrator, b"r" * 32)
        administrator.status = "locked"
        administrator.failed_attempts = 5
        administrator.lock_expires_at = datetime.now(UTC) + timedelta(minutes=15)
        db.session.commit()

    result = app.test_cli_runner().invoke(
        args=[
            "admin",
            "reset-password",
            "enrollment.admin",
            "--operator",
            OPERATOR,
            "--reason",
            REASON,
        ],
        input=f"{RESET_PASSWORD}\n{RESET_PASSWORD}\n",
    )

    assert result.exit_code == 0
    assert "revoked sessions: 1" in result.output
    assert RESET_PASSWORD not in result.output

    with app.app_context():
        administrator = _load_administrator()
        session = db.session.execute(select(AdministratorSession)).scalar_one()
        events = db.session.execute(
            select(AdministratorAuthenticationEvent.category)
        ).scalars()
        assert administrator.status == "active"
        assert administrator.failed_attempts == 0
        assert administrator.lock_expires_at is None
        assert check_password_hash(administrator.password_verifier, RESET_PASSWORD)
        assert session.revoked_at is not None
        assert session.revoked_by_operator_subject == OPERATOR
        assert "password_reset" in set(events)


def test_disable_account_revokes_sessions_and_records_event(app: Flask) -> None:
    assert _invoke_bootstrap(app).exit_code == 0
    with app.app_context():
        administrator = _load_administrator()
        _add_active_session(administrator, b"d" * 32)

    result = app.test_cli_runner().invoke(
        args=[
            "admin",
            "disable",
            "enrollment.admin",
            "--operator",
            OPERATOR,
            "--reason",
            REASON,
        ]
    )

    assert result.exit_code == 0
    assert "revoked sessions: 1" in result.output
    with app.app_context():
        administrator = _load_administrator()
        session = db.session.execute(select(AdministratorSession)).scalar_one()
        categories = set(
            db.session.execute(
                select(AdministratorAuthenticationEvent.category)
            ).scalars()
        )
        assert administrator.status == "disabled"
        assert administrator.disabled_at is not None
        assert session.revoked_at is not None
        assert "account_disabled" in categories


def test_revoke_sessions_records_zero_or_more_revocations(app: Flask) -> None:
    assert _invoke_bootstrap(app).exit_code == 0
    with app.app_context():
        administrator = _load_administrator()
        _add_active_session(administrator, b"s" * 32)

    result = app.test_cli_runner().invoke(
        args=[
            "admin",
            "revoke-sessions",
            "enrollment.admin",
            "--operator",
            OPERATOR,
            "--reason",
            REASON,
        ]
    )

    assert result.exit_code == 0
    assert "sessions revoked: 1" in result.output
    with app.app_context():
        session = db.session.execute(select(AdministratorSession)).scalar_one()
        assert session.revoked_at is not None
        assert session.revocation_reason == REASON


def test_bootstrap_rolls_back_all_rows_after_database_failure(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with app.app_context():
        original_commit = db.session.commit

        def fail_commit() -> None:
            raise SQLAlchemyError("forced test failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(AdministratorDatabaseError):
            bootstrap_administrator(
                username="enrollment.admin",
                display_name="Enrollment Administrator",
                password=BOOTSTRAP_PASSWORD,
                operator_subject=OPERATOR,
                reason=REASON,
            )
        monkeypatch.setattr(db.session, "commit", original_commit)

        administrator_count = db.session.scalar(
            select(func.count()).select_from(Administrator)
        )
        event_count = db.session.scalar(
            select(func.count()).select_from(AdministratorAuthenticationEvent)
        )
        assert administrator_count == 0
        assert event_count == 0
        assert BOOTSTRAP_PASSWORD not in caplog.text


@pytest.mark.parametrize(
    "password",
    ["short", "administrator", "password1234", "enrollment.admin"],
)
def test_bootstrap_rejects_weak_or_identity_passwords(
    app: Flask,
    password: str,
) -> None:
    with app.app_context(), pytest.raises(AdministratorOperationError):
        bootstrap_administrator(
            username="enrollment.admin",
            display_name="Enrollment Administrator",
            password=password,
            operator_subject=OPERATOR,
            reason=REASON,
        )

    with app.app_context():
        count = db.session.scalar(select(func.count()).select_from(Administrator))
        assert count == 0
