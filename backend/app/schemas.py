from dataclasses import dataclass
from uuid import UUID

from flask import Request
from werkzeug.exceptions import BadRequest

REGISTRATION_FIELDS = frozenset({"device_uuid", "android_version"})
ANDROID_VERSION_MAX_LENGTH = 32


@dataclass(frozen=True, slots=True)
class DeviceRegistrationData:
    device_uuid: UUID
    android_version: str


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

    device_uuid = _validate_device_uuid(payload["device_uuid"])
    android_version = _validate_android_version(payload["android_version"])

    return DeviceRegistrationData(
        device_uuid=device_uuid,
        android_version=android_version,
    )


def _validate_device_uuid(value: object) -> UUID:
    if not isinstance(value, str) or not value:
        raise DeviceRegistrationValidationError("device_uuid must be a valid UUID")

    try:
        return UUID(value)
    except (AttributeError, ValueError) as error:
        raise DeviceRegistrationValidationError(
            "device_uuid must be a valid UUID"
        ) from error


def _validate_android_version(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeviceRegistrationValidationError(
            "android_version must be a non-empty string"
        )

    normalized_value = value.strip()
    if len(normalized_value) > ANDROID_VERSION_MAX_LENGTH:
        raise DeviceRegistrationValidationError(
            "android_version must not exceed 32 characters"
        )
    return normalized_value


__all__ = [
    "DeviceRegistrationData",
    "DeviceRegistrationValidationError",
    "validate_device_registration_request",
]
