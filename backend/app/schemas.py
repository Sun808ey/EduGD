from dataclasses import dataclass
from uuid import UUID

from flask import Request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.device_identity import (
    ANDROID_VERSION_BY_API_LEVEL,
    parse_canonical_uuid4,
)

REGISTRATION_FIELDS = frozenset({"device_uuid", "android_version", "api_level"})


@dataclass(frozen=True, slots=True)
class DeviceRegistrationData:
    device_uuid: UUID
    android_version: str
    api_level: int


class DeviceRegistrationValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_device_registration_request(
    incoming_request: Request,
) -> DeviceRegistrationData:
    if incoming_request.mimetype != "application/json":
        raise DeviceRegistrationValidationError(
            "Content-Type must be application/json",
            status_code=415,
        )

    try:
        payload = incoming_request.get_json(silent=False)
    except RequestEntityTooLarge as error:
        raise DeviceRegistrationValidationError(
            "request body must not exceed 16 KiB",
            status_code=413,
        ) from error
    except BadRequest as error:
        raise DeviceRegistrationValidationError(
            "request body must contain valid JSON"
        ) from error

    if not isinstance(payload, dict):
        raise DeviceRegistrationValidationError("JSON body must be an object")

    unexpected_fields = sorted(set(payload) - REGISTRATION_FIELDS)
    if unexpected_fields:
        field_names = ", ".join(unexpected_fields)
        raise DeviceRegistrationValidationError(f"unexpected fields: {field_names}")

    if "device_uuid" not in payload:
        raise DeviceRegistrationValidationError("device_uuid is required")
    if "android_version" not in payload:
        raise DeviceRegistrationValidationError("android_version is required")
    if "api_level" not in payload:
        raise DeviceRegistrationValidationError("api_level is required")

    device_uuid = _validate_device_uuid(payload["device_uuid"])
    android_version, api_level = _validate_android_version(
        payload["android_version"],
        payload["api_level"],
    )

    return DeviceRegistrationData(
        device_uuid=device_uuid,
        android_version=android_version,
        api_level=api_level,
    )


def _validate_device_uuid(value: object) -> UUID:
    try:
        return parse_canonical_uuid4(value)
    except ValueError as error:
        raise DeviceRegistrationValidationError(
            "device_uuid must be a canonical UUID version 4"
        ) from error


def _validate_android_version(
    android_version: object,
    api_level: object,
) -> tuple[str, int]:
    if (
        not isinstance(android_version, str)
        or isinstance(api_level, bool)
        or not isinstance(api_level, int)
        or ANDROID_VERSION_BY_API_LEVEL.get(api_level) != android_version
    ):
        raise DeviceRegistrationValidationError(
            "android_version and api_level must identify a supported Android "
            "version and API level"
        )
    return android_version, api_level


__all__ = [
    "DeviceRegistrationData",
    "DeviceRegistrationValidationError",
    "validate_device_registration_request",
]
