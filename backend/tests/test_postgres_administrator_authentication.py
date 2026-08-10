from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import Mock

import pytest
from flask import Flask, jsonify
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from werkzeug.security import generate_password_hash

from app.administrator_authorization import administrator_required
from app.extensions import db
from app.models import (
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    AdministratorSession,
    DeviceEnrollmentEvent,
    EnrollmentToken,
)
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

pytestmark = pytest.mark.postgres

USERNAME = "postgres.admin"
PASSWORD = "OfflineSchool!2026"
WRONG_PASSWORD = "IncorrectSchool!2026"
REMOTE_ADDRESS = "192.0.2.40"
ADMINISTRATOR_TABLES = (
    Administrator,
    AdministratorPermission,
    AdministratorSession,
    AdministratorAuthenticationEvent,
    EnrollmentToken,
    DeviceEnrollmentEvent,
)


def _table_counts(connection: Connection) -> tuple[int, ...]:
    return tuple(
        connection.scalar(select(func.count()).select_from(model)) or 0
        for model in ADMINISTRATOR_TABLES
    )


@contextmanager
def _isolated_application_session(
    engine: Engine,
) -> Iterator[scoped_session[Session]]:
    """Bind application commits to savepoints inside a rolled-back transaction."""
    approved = validate_postgres_test_environment(require_destructive=True)
    with engine.connect() as verification_connection:
        validate_connected_postgres_test_environment(
            verification_connection,
            approved,
            require_destructive=True,
        )
        before_counts = _table_counts(verification_connection)

    connection = engine.connect()
    outer_transaction = None
    application_session: scoped_session[Session] | None = None
    original_session = db.session
    try:
        validate_connected_postgres_test_environment(
            connection,
            approved,
            require_destructive=True,
        )
        outer_transaction = connection.begin()
        connection.exec_driver_sql("SET TRANSACTION READ WRITE")
        application_session = scoped_session(
            sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
        )
        db.session = cast(Any, application_session)
        yield application_session
    finally:
        if application_session is not None:
            application_session.remove()
        db.session = original_session
        if outer_transaction is not None and outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()

        if outer_transaction is None or outer_transaction.is_active:
            raise AssertionError("PostgreSQL outer transaction was not rolled back")
        if not connection.closed:
            raise AssertionError(
                "PostgreSQL application test connection was not closed"
            )

        with engine.connect() as verification_connection:
            after_counts = _table_counts(verification_connection)
        if after_counts != before_counts:
            raise AssertionError(
                "PostgreSQL administrator test data persisted after rollback"
            )


@pytest.fixture()
def postgres_authentication_app(
    postgres_app: Flask,
    postgres_engine: Engine,
) -> Iterator[Flask]:
    with _isolated_application_session(postgres_engine):
        yield postgres_app


def _bootstrap() -> None:
    administrator = Administrator(
        username=USERNAME,
        display_name="PostgreSQL Administrator",
        password_verifier=generate_password_hash(PASSWORD, method="scrypt"),
    )
    db.session.add(administrator)
    db.session.flush()
    db.session.add(
        AdministratorPermission(
            administrator_id=administrator.id,
            permission="administrator.manage",
            trusted_operator_subject="postgres-test-operator",
            reason="PostgreSQL administrator authentication integration test",
        )
    )
    db.session.commit()


def _login(
    app: Flask,
    *,
    username: str = USERNAME,
    password: str = PASSWORD,
) -> Any:
    return app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": REMOTE_ADDRESS},
    )


def _authorization_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _administrator() -> Administrator:
    return db.session.execute(
        select(Administrator).where(Administrator.username == USERNAME)
    ).scalar_one()


def test_service_commits_remain_in_outer_transaction(
    postgres_authentication_app: Flask,
    postgres_engine: Engine,
) -> None:
    _bootstrap()

    response = _login(postgres_authentication_app)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert db.session.scalar(select(func.count()).select_from(Administrator)) == 1
    assert (
        db.session.scalar(select(func.count()).select_from(AdministratorSession)) == 1
    )
    with postgres_engine.connect() as independent_connection:
        assert (
            independent_connection.scalar(
                select(func.count())
                .select_from(Administrator)
                .where(Administrator.username == USERNAME)
            )
            == 0
        )


def test_lockout_uses_postgres_row_lock_and_persists_bounded_state(
    postgres_authentication_app: Flask,
) -> None:
    _bootstrap()

    failures = [
        _login(postgres_authentication_app, password=WRONG_PASSWORD) for _ in range(5)
    ]
    locked = _login(postgres_authentication_app, password=PASSWORD)

    assert all(response.status_code == 401 for response in failures)
    assert all(
        response.get_json() == {"error": "authentication_failed"}
        for response in failures
    )
    assert locked.status_code == 401
    assert locked.get_json() == {"error": "authentication_failed"}
    administrator = _administrator()
    assert administrator.status == "locked"
    assert administrator.failed_attempts == 5
    assert administrator.lock_expires_at is not None
    categories = list(
        db.session.execute(select(AdministratorAuthenticationEvent.category)).scalars()
    )
    assert categories.count("login_failed") == 6
    assert categories.count("account_locked") == 1


def test_authorization_rechecks_postgres_permissions_for_each_request(
    postgres_authentication_app: Flask,
) -> None:
    @administrator_required("administrator.manage")
    def protected() -> Any:
        return jsonify({"allowed": True})

    _bootstrap()
    access_token = _login(postgres_authentication_app).get_json()["access_token"]
    headers = _authorization_header(access_token)

    with postgres_authentication_app.test_request_context(headers=headers):
        allowed = postgres_authentication_app.make_response(protected())

    administrator = _administrator()
    db.session.execute(
        delete(AdministratorPermission).where(
            AdministratorPermission.administrator_id == administrator.id,
            AdministratorPermission.permission == "administrator.manage",
        )
    )
    db.session.commit()

    with postgres_authentication_app.test_request_context(headers=headers):
        denied = postgres_authentication_app.make_response(protected())

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.get_json() == {"error": "authorization_failed"}
    assert denied.headers["Cache-Control"] == "no-store"
    event = db.session.execute(
        select(AdministratorAuthenticationEvent).where(
            AdministratorAuthenticationEvent.category == "authorization_failed"
        )
    ).scalar_one()
    assert event.failure_class == "permission_denied"
    assert event.acting_administrator_id == administrator.id


def test_unique_session_failure_rolls_back_only_the_failed_login(
    postgres_authentication_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bootstrap()
    monkeypatch.setattr(
        "app.services.administrator_login.digest_jti",
        lambda _jti: b"x" * 32,
    )

    first = _login(postgres_authentication_app)
    second = _login(postgres_authentication_app)

    assert first.status_code == 200
    assert second.status_code == 500
    assert second.get_json() == {"error": "internal_server_error"}
    assert "access_token" not in second.get_data(as_text=True)
    assert (
        db.session.scalar(select(func.count()).select_from(AdministratorSession)) == 1
    )
    assert (
        db.session.scalar(
            select(func.count())
            .select_from(AdministratorAuthenticationEvent)
            .where(AdministratorAuthenticationEvent.category == "login_succeeded")
        )
        == 1
    )


def test_postgres_failure_audit_data_and_logs_are_redacted(
    postgres_authentication_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bootstrap()
    log_outcome = Mock()
    monkeypatch.setattr(
        "app.services.administrator_login._log_outcome",
        log_outcome,
    )

    known = _login(postgres_authentication_app, password=WRONG_PASSWORD)
    unknown = _login(
        postgres_authentication_app,
        username="unknown.postgres.admin",
        password=WRONG_PASSWORD,
    )

    assert known.status_code == unknown.status_code == 401
    assert known.get_json() == unknown.get_json() == {"error": "authentication_failed"}
    response_text = known.get_data(as_text=True) + unknown.get_data(as_text=True)
    assert USERNAME not in response_text
    assert "unknown.postgres.admin" not in response_text
    assert PASSWORD not in response_text
    assert WRONG_PASSWORD not in response_text

    events = list(
        db.session.execute(
            select(AdministratorAuthenticationEvent).where(
                AdministratorAuthenticationEvent.category == "login_failed"
            )
        ).scalars()
    )
    assert len(events) == 2
    assert any(event.administrator_id is None for event in events)
    assert all(event.failure_class == "invalid_credentials" for event in events)
    assert all(
        event.source_address_pseudonym is not None
        and len(event.source_address_pseudonym) == 32
        and REMOTE_ADDRESS.encode() not in event.source_address_pseudonym
        for event in events
    )
    assert "submitted_username" not in AdministratorAuthenticationEvent.__table__.c

    logged_values = repr(log_outcome.call_args_list)
    assert log_outcome.call_count == 2
    assert USERNAME not in logged_values
    assert "unknown.postgres.admin" not in logged_values
    assert PASSWORD not in logged_values
    assert WRONG_PASSWORD not in logged_values
    assert REMOTE_ADDRESS not in logged_values


def test_authorized_pairing_token_issuance_is_transactionally_isolated(
    postgres_authentication_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        postgres_authentication_app.config,
        "ENROLLMENT_ADMIN_ENABLED",
        True,
    )
    monkeypatch.setitem(
        postgres_authentication_app.config,
        "PAIRING_TOKEN_PEPPER",
        "postgres-integration-test-pairing-token-pepper",
    )
    _bootstrap()
    administrator = _administrator()
    db.session.add(
        AdministratorPermission(
            administrator_id=administrator.id,
            permission="enrollment_token.issue",
            trusted_operator_subject="postgres-test-operator",
            reason="PostgreSQL pairing-token issuance integration test",
        )
    )
    db.session.commit()
    access_token = _login(postgres_authentication_app).get_json()["access_token"]

    response = postgres_authentication_app.test_client().post(
        "/api/v1/admin/enrollment-tokens",
        json={"reason": "Provision a PostgreSQL integration-test device"},
        headers=_authorization_header(access_token),
    )

    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    pairing_token = response.get_json()["pairing_token"]
    token = db.session.execute(select(EnrollmentToken)).scalar_one()
    event = db.session.execute(select(DeviceEnrollmentEvent)).scalar_one()
    assert len(token.verifier) == 32
    assert pairing_token not in repr(token.__dict__)
    assert event.category == "token_issued"
    assert event.token_id == token.id
    assert event.administrator_subject == str(administrator.administrator_uuid)
