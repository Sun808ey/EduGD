import json
from typing import Any

import pytest
from flask import Flask, request
from flask.ctx import RequestContext

from app.device_identity import ANDROID_VERSION_BY_API_LEVEL
from app.schemas import (
    DeviceRegistrationValidationError,
    validate_device_registration_request,
)

DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"
VALID_PAYLOAD: dict[str, Any] = {
    "device_uuid": DEVICE_UUID,
    "android_version": "10",
    "api_level": 29,
}


def request_context(
    app: Flask,
    *,
    payload: Any,
) -> RequestContext:
    return app.test_request_context(
        "/api/v1/devices/register",
        method="POST",
        data=json.dumps(payload),
        content_type="application/json",
    )


def test_valid_registration_request_is_preserved(app: Flask) -> None:
    with request_context(app, payload=VALID_PAYLOAD):
        validated = validate_device_registration_request(request)

    assert str(validated.device_uuid) == VALID_PAYLOAD["device_uuid"]
    assert validated.android_version == "10"
    assert validated.api_level == 29


@pytest.mark.parametrize(
    ("api_level", "android_version"),
    sorted(ANDROID_VERSION_BY_API_LEVEL.items()),
)
def test_registration_accepts_supported_android_compatibility(
    app: Flask,
    api_level: int,
    android_version: str,
) -> None:
    payload = {
        **VALID_PAYLOAD,
        "android_version": android_version,
        "api_level": api_level,
    }

    with request_context(app, payload=payload):
        validated = validate_device_registration_request(request)

    assert validated.android_version == android_version
    assert validated.api_level == api_level


@pytest.mark.parametrize(
    "content_type",
    [None, "text/plain", "application/vnd.api+json"],
)
def test_registration_requires_application_json(
    app: Flask,
    content_type: str | None,
) -> None:
    with app.test_request_context(
        "/api/v1/devices/register",
        method="POST",
        data="{}",
        content_type=content_type,
    ):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.status_code == 415
    assert error.value.message == "Content-Type must be application/json"


def test_registration_rejects_malformed_json(app: Flask) -> None:
    with app.test_request_context(
        "/api/v1/devices/register",
        method="POST",
        data='{"device_uuid":',
        content_type="application/json",
    ):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.status_code == 400
    assert error.value.message == "request body must contain valid JSON"


@pytest.mark.parametrize("payload", [None, [], "value", 10, True])
def test_registration_requires_json_object(app: Flask, payload: Any) -> None:
    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.status_code == 400
    assert error.value.message == "JSON body must be an object"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"android_version": "10"}, "device_uuid is required"),
        (
            {"device_uuid": VALID_PAYLOAD["device_uuid"]},
            "android_version is required",
        ),
        (
            {
                "device_uuid": VALID_PAYLOAD["device_uuid"],
                "android_version": "10",
            },
            "api_level is required",
        ),
    ],
)
def test_registration_requires_both_fields(
    app: Flask,
    payload: dict[str, Any],
    message: str,
) -> None:
    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.message == message


@pytest.mark.parametrize(
    "device_uuid",
    [
        None,
        10,
        "",
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        DEVICE_UUID.upper(),
        "{550e8400-e29b-41d4-a716-446655440000}",
        "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
        "550e8400e29b41d4a716446655440000",
    ],
)
def test_registration_rejects_invalid_uuid(
    app: Flask,
    device_uuid: Any,
) -> None:
    payload = {**VALID_PAYLOAD, "device_uuid": device_uuid}

    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.message == "device_uuid must be a canonical UUID version 4"


@pytest.mark.parametrize(
    ("android_version", "api_level"),
    [
        (None, 29),
        (10, 29),
        ("", 29),
        (" 10 ", 29),
        ("4.4", 20),
        ("11", 30),
        ("10", 28),
        ("9", 29),
        ("10", True),
        ("10", "29"),
    ],
)
def test_registration_rejects_invalid_android_compatibility(
    app: Flask,
    android_version: Any,
    api_level: Any,
) -> None:
    payload = {
        **VALID_PAYLOAD,
        "android_version": android_version,
        "api_level": api_level,
    }

    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.message == (
        "android_version and api_level must identify Android 5.0 through "
        "10.0 (API 21 through 29)"
    )


@pytest.mark.parametrize("field", ["id", "status", "created_at", "extra"])
def test_registration_rejects_unexpected_client_fields(
    app: Flask,
    field: str,
) -> None:
    payload = {**VALID_PAYLOAD, field: "untrusted"}

    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.message == f"unexpected fields: {field}"
