from __future__ import annotations

from dataclasses import dataclass

from flask import Request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.device_identity import parse_canonical_uuid4, validate_android_compatibility


class EnrollmentValidationError(ValueError):
    def __init__(self, status_code: int = 400) -> None:
        super().__init__("invalid enrollment request")
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class EnrollmentCredentialData:
    algorithm: str
    public_key: str
    nonce: str
    proof: str


@dataclass(frozen=True, slots=True)
class DeviceEnrollmentData:
    device_uuid: str
    android_version: str
    api_level: int
    pairing_token: str
    credential: EnrollmentCredentialData


@dataclass(frozen=True, slots=True)
class TokenIssueData:
    reason: str
    bound_device_uuid: str | None


@dataclass(frozen=True, slots=True)
class ReasonData:
    reason: str


@dataclass(frozen=True, slots=True)
class RotationData:
    algorithm: str
    public_key: str
    nonce: str
    proof: str


def _json_object(incoming_request: Request) -> dict[str, object]:
    if incoming_request.mimetype != "application/json":
        raise EnrollmentValidationError(415)
    try:
        payload = incoming_request.get_json(silent=False)
    except RequestEntityTooLarge as error:
        raise EnrollmentValidationError(413) from error
    except BadRequest as error:
        raise EnrollmentValidationError() from error
    if not isinstance(payload, dict):
        raise EnrollmentValidationError()
    return payload


def _exact_fields(
    payload: dict[str, object], required: set[str], optional: set[str] | None = None
) -> None:
    optional = optional or set()
    if not required.issubset(payload) or set(payload) - required - optional:
        raise EnrollmentValidationError()


def _bounded_text(value: object, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or not value.isprintable()
    ):
        raise EnrollmentValidationError()
    return value


def validate_enrollment_request(incoming_request: Request) -> DeviceEnrollmentData:
    payload = _json_object(incoming_request)
    _exact_fields(
        payload,
        {"device_uuid", "android_version", "api_level", "pairing_token", "credential"},
    )
    try:
        device_uuid = str(parse_canonical_uuid4(payload["device_uuid"]))
        android_version, api_level = validate_android_compatibility(
            payload["android_version"], payload["api_level"]
        )
    except ValueError as error:
        raise EnrollmentValidationError() from error
    pairing_token = _bounded_text(payload["pairing_token"], 80)
    credential_payload = payload["credential"]
    if not isinstance(credential_payload, dict):
        raise EnrollmentValidationError()
    _exact_fields(credential_payload, {"algorithm", "public_key", "nonce", "proof"})
    credential = EnrollmentCredentialData(
        algorithm=_bounded_text(credential_payload["algorithm"], 32),
        public_key=_bounded_text(credential_payload["public_key"], 700),
        nonce=_bounded_text(credential_payload["nonce"], 22),
        proof=_bounded_text(credential_payload["proof"], 342),
    )
    return DeviceEnrollmentData(
        device_uuid,
        android_version,
        api_level,
        pairing_token,
        credential,
    )


def validate_token_issue_request(incoming_request: Request) -> TokenIssueData:
    payload = _json_object(incoming_request)
    _exact_fields(payload, {"reason"}, {"bound_device_uuid"})
    bound_value = payload.get("bound_device_uuid")
    try:
        bound_uuid = (
            None if bound_value is None else str(parse_canonical_uuid4(bound_value))
        )
    except ValueError as error:
        raise EnrollmentValidationError() from error
    return TokenIssueData(_bounded_text(payload["reason"], 512), bound_uuid)


def validate_reason_request(incoming_request: Request) -> ReasonData:
    payload = _json_object(incoming_request)
    _exact_fields(payload, {"reason"})
    return ReasonData(_bounded_text(payload["reason"], 512))


def validate_rotation_request(incoming_request: Request) -> RotationData:
    payload = _json_object(incoming_request)
    _exact_fields(payload, {"algorithm", "public_key", "nonce", "proof"})
    return RotationData(
        _bounded_text(payload["algorithm"], 32),
        _bounded_text(payload["public_key"], 700),
        _bounded_text(payload["nonce"], 22),
        _bounded_text(payload["proof"], 342),
    )


__all__ = [
    "DeviceEnrollmentData",
    "EnrollmentValidationError",
    "ReasonData",
    "RotationData",
    "TokenIssueData",
    "validate_enrollment_request",
    "validate_reason_request",
    "validate_rotation_request",
    "validate_token_issue_request",
]
