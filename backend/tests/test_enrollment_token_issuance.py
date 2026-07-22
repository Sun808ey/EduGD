from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID

import pytest
from flask import Flask
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    Device,
    DeviceEnrollmentEvent,
    EnrollmentToken,
)
from app.services.administrator_authentication import bootstrap_administrator

USERNAME = "token.issuer"
PASSWORD = "OfflineSchool!2026"
DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"
REASON = "Provision a school-owned examination device"


def _bootstrap_and_login(app: Flask) -> str:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="Enrollment Token Issuer",
            password=PASSWORD,
            operator_subject="test-operator",
            reason="pairing-token issuance test",
        )
    response = app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    assert response.status_code == 200
    payload = cast(dict[str, Any], response.get_json())
    return cast(str, payload["access_token"])


def _issue(
    app: Flask,
    access_token: str,
    *,
    bound_device_uuid: str | None = None,
) -> Any:
    payload = {"reason": REASON}
    if bound_device_uuid is not None:
        payload["bound_device_uuid"] = bound_device_uuid
    return app.test_client().post(
        "/api/v1/admin/enrollment-tokens",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _decode_secret(pairing_token: str) -> bytes:
    encoded = pairing_token.split(".", 1)[1]
    return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))


def test_authorized_issuance_returns_secret_once_and_stores_only_verifier(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access_token = _bootstrap_and_login(app)
    log_sink = Mock()
    for method_name in ("debug", "info", "warning", "error", "critical", "exception"):
        monkeypatch.setattr(app.logger, method_name, log_sink)

    response = _issue(app, access_token)

    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    payload = cast(dict[str, Any], response.get_json())
    pairing_token = cast(str, payload["pairing_token"])
    token_uuid, encoded_secret = pairing_token.split(".", 1)
    secret = _decode_secret(pairing_token)
    assert payload["token_uuid"] == token_uuid
    assert payload["bound_device_uuid"] is None
    assert len(secret) == 32
    assert "=" not in encoded_secret
    assert response.get_data(as_text=True).count(pairing_token) == 1
    assert pairing_token not in repr(log_sink.call_args_list)

    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        event = db.session.execute(select(DeviceEnrollmentEvent)).scalar_one()
        administrator = db.session.execute(select(Administrator)).scalar_one()
        assert str(token.token_uuid) == token_uuid
        assert len(token.verifier) == 32
        assert token.verifier != secret
        assert token.status == "active"
        assert token.failed_attempts == 0
        assert token.reason == REASON
        assert token.issued_by == str(administrator.administrator_uuid)
        assert event.category == "token_issued"
        assert event.token_id == token.id
        assert event.administrator_subject == str(administrator.administrator_uuid)
        assert event.reason == REASON
        assert "pairing_token" not in EnrollmentToken.__table__.c
        assert pairing_token not in repr(token.__dict__)
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        remaining_seconds = (expires_at - datetime.now(UTC)).total_seconds()
        assert 0 < remaining_seconds <= app.config["ENROLLMENT_TOKEN_TTL_SECONDS"]


def test_issuance_requires_current_database_permission(app: Flask) -> None:
    access_token = _bootstrap_and_login(app)
    with app.app_context():
        administrator_id = db.session.scalar(select(Administrator.id))
        db.session.execute(
            delete(AdministratorPermission).where(
                AdministratorPermission.administrator_id == administrator_id,
                AdministratorPermission.permission == "enrollment_token.issue",
            )
        )
        db.session.commit()

    response = _issue(app, access_token)

    assert response.status_code == 403
    assert response.get_json() == {"error": "authorization_failed"}
    assert response.headers["Cache-Control"] == "no-store"
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(EnrollmentToken)) == 0
        event = db.session.execute(
            select(AdministratorAuthenticationEvent).where(
                AdministratorAuthenticationEvent.category == "authorization_failed"
            )
        ).scalar_one()
        assert event.failure_class == "permission_denied"


def test_issuance_can_bind_token_to_an_existing_device(app: Flask) -> None:
    access_token = _bootstrap_and_login(app)
    with app.app_context():
        device = Device(
            device_uuid=UUID(DEVICE_UUID),
            android_version="10",
            api_level=29,
            status="active",
        )
        db.session.add(device)
        db.session.commit()
        device_id = device.id

    response = _issue(app, access_token, bound_device_uuid=DEVICE_UUID)

    assert response.status_code == 201
    assert response.get_json()["bound_device_uuid"] == DEVICE_UUID
    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        event = db.session.execute(select(DeviceEnrollmentEvent)).scalar_one()
        assert token.bound_device_id == device_id
        assert event.device_id == device_id
        assert event.token_id == token.id


def test_issuance_transaction_rolls_back_token_and_event_on_commit_failure(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access_token = _bootstrap_and_login(app)
    with app.app_context():
        original_commit = db.session.commit

        def fail_commit() -> None:
            raise SQLAlchemyError("forced issuance commit failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        response = _issue(app, access_token)
        monkeypatch.setattr(db.session, "commit", original_commit)

        assert response.status_code == 500
        assert response.get_json() == {"error": "internal_server_error"}
        assert response.headers["Cache-Control"] == "no-store"
        assert "pairing_token" not in response.get_data(as_text=True)
        assert db.session.scalar(select(func.count()).select_from(EnrollmentToken)) == 0
        assert (
            db.session.scalar(
                select(func.count())
                .select_from(DeviceEnrollmentEvent)
                .where(DeviceEnrollmentEvent.category == "token_issued")
            )
            == 0
        )
