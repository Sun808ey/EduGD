import json
from typing import Any

import pytest
from flask import Flask, request
from flask.ctx import RequestContext

from app.schemas import (
    DeviceRegistrationValidationError,
    validate_device_registration_request,
)


VALID_PAYLOAD = {
    "device_uuid": "550E8400-E29B-41D4-A716-446655440000",
    "android_version": "10",
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


def test_valid_registration_request_is_normalized(app: Flask) -> None:
    payload = {**VALID_PAYLOAD, "android_version": " 10 "}

    with request_context(app, payload=payload):
        validated = validate_device_registration_request(request)

    assert str(validated.device_uuid) == VALID_PAYLOAD["device_uuid"].lower()
    assert validated.android_version == "10"


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


@pytest.mark.parametrize("device_uuid", [None, 10, "", "not-a-uuid"])
def test_registration_rejects_invalid_uuid(
    app: Flask,
    device_uuid: Any,
) -> None:
    payload = {**VALID_PAYLOAD, "device_uuid": device_uuid}

    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.message == "device_uuid must be a valid UUID"


@pytest.mark.parametrize("android_version", [None, 10, "", "   "])
def test_registration_rejects_invalid_android_version(
    app: Flask,
    android_version: Any,
) -> None:
    payload = {**VALID_PAYLOAD, "android_version": android_version}

    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.message == "android_version must be a non-empty string"


def test_registration_rejects_android_version_over_model_limit(
    app: Flask,
) -> None:
    payload = {**VALID_PAYLOAD, "android_version": "1" * 33}

    with request_context(app, payload=payload):
        with pytest.raises(DeviceRegistrationValidationError) as error:
            validate_device_registration_request(request)

    assert error.value.message == "android_version must not exceed 32 characters"


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
