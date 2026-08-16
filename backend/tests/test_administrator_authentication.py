from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from flask import Flask, jsonify
from flask_jwt_extended import create_access_token, decode_token
from flask_migrate import upgrade
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.administrator_authorization import administrator_required
from app.extensions import db
from app.models import (
    ADMINISTRATOR_PERMISSIONS,
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    AdministratorSession,
)
from app.services.administrator_authentication import bootstrap_administrator
from app.services.administrator_login import digest_jti

USERNAME = "enrollment.admin"
PASSWORD = "OfflineSchool!2026"
WRONG_PASSWORD = "IncorrectSchool!2026"
REMOTE_ADDRESS = "192.0.2.40"


def _bootstrap(app: Flask) -> None:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="Enrollment Administrator",
            password=PASSWORD,
            operator_subject="test-host-operator",
            reason="administrator authentication test bootstrap",
        )


def _login(
    app: Flask,
    *,
    username: str = USERNAME,
    password: str = PASSWORD,
    remote_address: str = REMOTE_ADDRESS,
) -> Any:
    return app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": remote_address},
    )


def _authorization_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _administrator() -> Administrator:
    return db.session.execute(
        select(Administrator).where(Administrator.username == USERNAME)
    ).scalar_one()


def test_successful_login_stores_only_jti_digest_and_returns_bounded_jwt(
    app: Flask,
) -> None:
    _bootstrap(app)

    response = _login(app)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    payload = response.get_json()
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == 900
    assert payload["administrator"]["username"] == USERNAME
    access_token = payload["access_token"]
    assert PASSWORD not in response.get_data(as_text=True)

    with app.app_context():
        claims = decode_token(access_token)
        assert claims["iss"] == "edug-school-policy-api"
        assert claims["aud"] == "edug-school-administration"
        assert "permissions" not in claims
        assert "role" not in claims
        assert "password" not in claims
        session = db.session.execute(select(AdministratorSession)).scalar_one()
        event = db.session.execute(
            select(AdministratorAuthenticationEvent).where(
                AdministratorAuthenticationEvent.category == "login_succeeded"
            )
        ).scalar_one()
        assert session.jti_digest == digest_jti(claims["jti"])
        assert session.source_address_pseudonym is not None
        assert REMOTE_ADDRESS.encode() not in session.source_address_pseudonym
        assert event.session_id == session.id


def test_me_requires_database_session_and_returns_current_permissions(
    app: Flask,
) -> None:
    _bootstrap(app)
    access_token = _login(app).get_json()["access_token"]

    response = app.test_client().get(
        "/api/v1/admin/auth/me",
        headers=_authorization_header(access_token),
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    administrator = response.get_json()["administrator"]
    assert administrator["username"] == USERNAME
    assert set(administrator["permissions"]) == ADMINISTRATOR_PERMISSIONS


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer malformed"},
        {"Authorization": "Basic unsupported"},
    ],
)
def test_missing_or_invalid_tokens_use_one_generic_response(
    app: Flask,
    headers: dict[str, str],
) -> None:
    response = app.test_client().get("/api/v1/admin/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_failed"
    assert response.headers["Cache-Control"] == "no-store"


def test_valid_signed_token_without_database_session_fails_closed(app: Flask) -> None:
    _bootstrap(app)
    with app.app_context():
        administrator = _administrator()
        access_token = create_access_token(
            identity=str(administrator.administrator_uuid)
        )

    response = app.test_client().get(
        "/api/v1/admin/auth/me",
        headers=_authorization_header(access_token),
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_failed"


def test_expired_token_uses_generic_failure_response(app: Flask) -> None:
    with app.app_context():
        access_token = create_access_token(
            identity="6fc82caf-4e5d-4a66-80dd-ae308ef53426",
            expires_delta=-timedelta(seconds=1),
        )

    response = app.test_client().get(
        "/api/v1/admin/auth/me",
        headers=_authorization_header(access_token),
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_failed"
    assert response.headers["Cache-Control"] == "no-store"


def test_unknown_and_wrong_password_responses_are_indistinguishable(app: Flask) -> None:
    _bootstrap(app)

    wrong_password = _login(app, password=WRONG_PASSWORD)
    unknown_account = _login(
        app,
        username="unknown.admin",
        password=WRONG_PASSWORD,
    )

    assert wrong_password.status_code == 401
    assert unknown_account.status_code == 401
    assert wrong_password.get_json() == unknown_account.get_json()
    assert wrong_password.get_json()["error"]["code"] == "authentication_failed"
    assert USERNAME not in wrong_password.get_data(as_text=True)
    assert "unknown.admin" not in unknown_account.get_data(as_text=True)

    with app.app_context():
        failures = list(
            db.session.execute(
                select(AdministratorAuthenticationEvent).where(
                    AdministratorAuthenticationEvent.category == "login_failed"
                )
            ).scalars()
        )
        assert len(failures) == 2
        assert any(event.administrator_id is None for event in failures)
        assert all(event.source_address_pseudonym is not None for event in failures)
        assert "submitted_username" not in AdministratorAuthenticationEvent.__table__.c


def test_login_operational_logs_exclude_credentials_and_username(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bootstrap(app)
    log_outcome = Mock()
    monkeypatch.setattr(
        "app.services.administrator_login._log_outcome",
        log_outcome,
    )

    response = _login(app, password=WRONG_PASSWORD)
    logged_values = repr(log_outcome.call_args_list)

    assert response.status_code == 401
    log_outcome.assert_called_once_with("administrator_login_failed")
    assert PASSWORD not in logged_values
    assert WRONG_PASSWORD not in logged_values
    assert USERNAME not in logged_values


def test_five_failed_logins_lock_account_without_revealing_state(app: Flask) -> None:
    _bootstrap(app)

    responses = [_login(app, password=WRONG_PASSWORD) for _ in range(5)]
    locked_response = _login(app, password=PASSWORD)

    assert all(response.status_code == 401 for response in responses)
    assert locked_response.status_code == 401
    assert locked_response.get_json()["error"]["code"] == "authentication_failed"
    with app.app_context():
        administrator = _administrator()
        assert administrator.status == "locked"
        assert administrator.failed_attempts == 5
        assert administrator.lock_expires_at is not None
        categories = list(
            db.session.execute(
                select(AdministratorAuthenticationEvent.category)
            ).scalars()
        )
        assert categories.count("account_locked") == 1


def test_valid_login_after_lock_expiry_unlocks_and_records_event(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bootstrap(app)
    now = datetime.now(UTC)
    with app.app_context():
        administrator = _administrator()
        administrator.status = "locked"
        administrator.failed_attempts = 5
        administrator.lock_expires_at = now + timedelta(minutes=1)
        db.session.commit()
    monkeypatch.setattr(
        "app.services.administrator_login.utc_now",
        lambda: now + timedelta(minutes=2),
    )

    response = _login(app)

    assert response.status_code == 200
    with app.app_context():
        administrator = _administrator()
        assert administrator.status == "active"
        assert administrator.failed_attempts == 0
        assert administrator.lock_expires_at is None
        categories = set(
            db.session.execute(
                select(AdministratorAuthenticationEvent.category)
            ).scalars()
        )
        assert "account_unlocked" in categories


def test_disabled_account_and_session_fail_closed(app: Flask) -> None:
    _bootstrap(app)
    access_token = _login(app).get_json()["access_token"]
    with app.app_context():
        administrator = _administrator()
        administrator.status = "disabled"
        administrator.disabled_at = datetime.now(UTC)
        db.session.commit()

    login_response = _login(app)
    session_response = app.test_client().get(
        "/api/v1/admin/auth/me",
        headers=_authorization_header(access_token),
    )

    assert login_response.status_code == 401
    assert session_response.status_code == 401
    assert (
        login_response.get_json()
        == session_response.get_json()
        == session_response.get_json()
    )
    assert login_response.get_json()["error"]["code"] == "authentication_failed"


def test_logout_revokes_database_session_and_rejects_token_reuse(app: Flask) -> None:
    _bootstrap(app)
    access_token = _login(app).get_json()["access_token"]
    headers = _authorization_header(access_token)

    logout_response = app.test_client().post(
        "/api/v1/admin/auth/logout",
        headers=headers,
    )
    reused_response = app.test_client().get(
        "/api/v1/admin/auth/me",
        headers=headers,
    )

    assert logout_response.status_code == 200
    assert logout_response.headers["Cache-Control"] == "no-store"
    assert reused_response.status_code == 401
    with app.app_context():
        session = db.session.execute(select(AdministratorSession)).scalar_one()
        assert session.revoked_at is not None
        assert session.revoked_by_administrator_id == session.administrator_id
        categories = set(
            db.session.execute(
                select(AdministratorAuthenticationEvent.category)
            ).scalars()
        )
        assert "logout" in categories
        assert "authorization_failed" in categories


def test_permission_decorator_uses_database_not_jwt_claims(app: Flask) -> None:
    @app.get("/test/admin-manage")
    @administrator_required("administrator.manage")
    def protected_test_route() -> Any:
        return jsonify({"allowed": True})

    _bootstrap(app)
    access_token = _login(app).get_json()["access_token"]
    headers = _authorization_header(access_token)
    allowed_response = app.test_client().get("/test/admin-manage", headers=headers)

    with app.app_context():
        administrator = _administrator()
        db.session.execute(
            delete(AdministratorPermission).where(
                AdministratorPermission.administrator_id == administrator.id,
                AdministratorPermission.permission == "administrator.manage",
            )
        )
        db.session.commit()

    denied_response = app.test_client().get("/test/admin-manage", headers=headers)

    assert allowed_response.status_code == 200
    assert denied_response.status_code == 403
    assert denied_response.get_json() == {"error": "authorization_failed"}
    assert denied_response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    ("content_type", "body", "expected_status"),
    [
        ("text/plain", "not-json", 415),
        ("application/json", "{", 400),
        ("application/json", "[]", 400),
        ("application/json", '{"username":"a"}', 400),
        (
            "application/json",
            '{"username":"a","password":"b","extra":true}',
            400,
        ),
    ],
)
def test_login_rejects_malformed_requests_without_details(
    app: Flask,
    content_type: str,
    body: str,
    expected_status: int,
) -> None:
    response = app.test_client().post(
        "/api/v1/admin/auth/login",
        data=body,
        content_type=content_type,
    )

    assert response.status_code == expected_status
    assert response.get_json()["error"]["code"] == "invalid_request"
    assert response.headers["Cache-Control"] == "no-store"


def test_login_rejects_body_over_16_kib(app: Flask) -> None:
    response = app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": "u" * 16_384, "password": "p"},
    )

    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_login_rate_limit_is_ten_per_source_per_minute() -> None:
    application = create_app("testing", {"RATELIMIT_ENABLED": True})
    with application.app_context():
        upgrade()

    client = application.test_client()
    responses = [
        client.post(
            "/api/v1/admin/auth/login",
            json={"username": "unknown.admin", "password": WRONG_PASSWORD},
            environ_base={"REMOTE_ADDR": "192.0.2.99"},
        )
        for _ in range(11)
    ]

    assert all(response.status_code == 401 for response in responses[:10])
    assert responses[10].status_code == 429
    assert responses[10].get_json()["error"]["code"] == "rate_limit_exceeded"
    assert responses[10].headers["Cache-Control"] == "no-store"


def test_login_database_failure_rolls_back_and_returns_no_token(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bootstrap(app)
    with app.app_context():
        original_commit = db.session.commit

        def fail_commit() -> None:
            raise SQLAlchemyError("forced test failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        response = _login(app)
        monkeypatch.setattr(db.session, "commit", original_commit)

        assert response.status_code == 500
        assert "access_token" not in response.get_data(as_text=True)
        session_count = db.session.scalar(
            select(func.count()).select_from(AdministratorSession)
        )
        success_count = db.session.scalar(
            select(func.count())
            .select_from(AdministratorAuthenticationEvent)
            .where(AdministratorAuthenticationEvent.category == "login_succeeded")
        )
        assert session_count == 0
        assert success_count == 0
