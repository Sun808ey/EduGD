from typing import Any
from uuid import UUID

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Device
from app.schemas import DeviceRegistrationData
from app.services import device_registration as registration_service

DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"
REGISTRATION_URL = "/api/v1/devices/register"
VALID_PAYLOAD = {
    "device_uuid": DEVICE_UUID,
    "android_version": "10",
    "api_level": 29,
}


def test_registers_new_device(client: FlaskClient, app: Flask) -> None:
    response = client.post(REGISTRATION_URL, json=VALID_PAYLOAD)

    assert response.status_code == 201
    assert response.get_json() == {
        "message": "device registered",
        "device": {
            "device_uuid": DEVICE_UUID,
            "android_version": "10",
            "api_level": 29,
            "status": "active",
        },
    }

    with app.app_context():
        device = db.session.execute(select(Device)).scalar_one()
        assert device.device_uuid == UUID(DEVICE_UUID)
        assert device.android_version == "10"
        assert device.api_level == 29
        assert device.status == "active"
        assert device.registered_at is not None
        assert device.created_at is not None
        assert device.updated_at is not None


def test_identical_registration_is_idempotent(
    client: FlaskClient,
    app: Flask,
) -> None:
    first_response = client.post(REGISTRATION_URL, json=VALID_PAYLOAD)
    second_response = client.post(REGISTRATION_URL, json=VALID_PAYLOAD)

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert second_response.get_json() == {
        "message": "device already registered",
        "device": {
            "device_uuid": DEVICE_UUID,
            "android_version": "10",
            "api_level": 29,
            "status": "active",
        },
    }

    with app.app_context():
        device_count = db.session.execute(
            select(func.count()).select_from(Device)
        ).scalar_one()
        assert device_count == 1


def test_existing_uuid_with_different_data_is_rejected(
    client: FlaskClient,
) -> None:
    client.post(REGISTRATION_URL, json=VALID_PAYLOAD)

    response = client.post(
        REGISTRATION_URL,
        json={**VALID_PAYLOAD, "android_version": "9", "api_level": 28},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "device UUID already registered with different data"
    }


@pytest.mark.parametrize(
    ("request_kwargs", "status_code", "error_message"),
    [
        (
            {"data": '{"device_uuid":', "content_type": "application/json"},
            400,
            "request body must contain valid JSON",
        ),
        (
            {"json": {"android_version": "10"}},
            400,
            "device_uuid is required",
        ),
        (
            {"json": {**VALID_PAYLOAD, "device_uuid": "invalid"}},
            400,
            "device_uuid must be a canonical UUID version 4",
        ),
        (
            {"data": "{}", "content_type": "text/plain"},
            415,
            "Content-Type must be application/json",
        ),
    ],
)
def test_registration_returns_validation_errors(
    client: FlaskClient,
    request_kwargs: dict[str, Any],
    status_code: int,
    error_message: str,
) -> None:
    response = client.post(REGISTRATION_URL, **request_kwargs)

    assert response.status_code == status_code
    assert response.get_json() == {"error": error_message}


def test_registration_database_failure_rolls_back(
    client: FlaskClient,
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback_calls = 0

    with app.app_context():
        original_rollback = db.session.rollback

        def fail_commit() -> None:
            raise SQLAlchemyError("forced database failure")

        def track_rollback() -> None:
            nonlocal rollback_calls
            rollback_calls += 1
            original_rollback()

        monkeypatch.setattr(db.session, "commit", fail_commit)
        monkeypatch.setattr(db.session, "rollback", track_rollback)
        app.logger.disabled = True

        response = client.post(REGISTRATION_URL, json=VALID_PAYLOAD)

        assert response.status_code == 500
        assert response.get_json() == {"error": "internal server error"}
        assert rollback_calls == 1
        assert db.session.execute(select(Device)).scalar_one_or_none() is None


def test_registration_rejects_body_over_endpoint_limit(
    client: FlaskClient,
) -> None:
    oversized_payload = {
        **VALID_PAYLOAD,
        "padding": "x" * (16 * 1_024),
    }

    response = client.post(REGISTRATION_URL, json=oversized_payload)

    assert response.status_code == 413
    assert response.get_json() == {"error": "request body must not exceed 16 KiB"}


def test_request_size_configuration(app: Flask) -> None:
    assert app.config["MAX_CONTENT_LENGTH"] == 1 * 1_024 * 1_024
    assert app.config["REGISTRATION_MAX_CONTENT_LENGTH"] == 16 * 1_024


def test_unique_constraint_race_returns_idempotent_result(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_device = Device(
        device_uuid=UUID(DEVICE_UUID),
        android_version="10",
        api_level=29,
        status="active",
    )
    lookup_results = iter([None, existing_device])
    rollback_calls = 0

    def find_device(_device_uuid: UUID) -> Device | None:
        return next(lookup_results)

    def fail_commit() -> None:
        raise IntegrityError("INSERT", {}, Exception("duplicate"))

    def track_rollback() -> None:
        nonlocal rollback_calls
        rollback_calls += 1

    with app.app_context():
        monkeypatch.setattr(registration_service, "_find_device", find_device)
        monkeypatch.setattr(db.session, "commit", fail_commit)
        monkeypatch.setattr(db.session, "rollback", track_rollback)

        result = registration_service.register_device(
            DeviceRegistrationData(
                device_uuid=UUID(DEVICE_UUID),
                android_version="10",
                api_level=29,
            )
        )

    assert result.created is False
    assert result.device.device_uuid == DEVICE_UUID
    assert rollback_calls == 1
