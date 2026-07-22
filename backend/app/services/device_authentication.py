from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Never, ParamSpec, TypeVar, cast
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from flask import Response, current_app, g, jsonify, request
from flask.typing import ResponseReturnValue
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.device_cryptography import (
    DeviceCryptographyError,
    canonicalize_request_target,
    decode_base64url,
    request_message,
)
from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    Device,
    DeviceCredential,
    DeviceEnrollmentEvent,
    DeviceRequestNonce,
    utc_now,
)


class DeviceAuthenticationFailed(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeviceAuthenticationContext:
    device: Device
    credential: DeviceCredential | None
    legacy: bool


P = ParamSpec("P")
R = TypeVar("R", bound=ResponseReturnValue)


def device_authentication_required(
    *,
    allowed_query_names: frozenset[str],
    allow_legacy: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, ResponseReturnValue]]:
    def decorator(function: Callable[P, R]) -> Callable[P, ResponseReturnValue]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
            device_uuid = kwargs.get("device_uuid")
            if not isinstance(device_uuid, str):
                return _failure_response()
            try:
                authenticate_device_request(
                    device_uuid,
                    allowed_query_names=allowed_query_names,
                    allow_legacy=allow_legacy,
                )
            except DeviceAuthenticationFailed:
                return _failure_response()
            return function(*args, **kwargs)

        return cast(Callable[P, ResponseReturnValue], wrapped)

    return decorator


def authenticate_device_request(
    device_uuid_text: str,
    *,
    allowed_query_names: frozenset[str],
    allow_legacy: bool = True,
) -> DeviceAuthenticationContext | None:
    mode = current_app.config["DEVICE_ENROLLMENT_MODE"]
    if mode == "legacy" and allow_legacy:
        return None
    try:
        device_uuid = parse_canonical_uuid4(device_uuid_text)
    except ValueError:
        _fail(None, None, "invalid_device")
    device = db.session.execute(
        select(Device).where(Device.device_uuid == device_uuid)
    ).scalar_one_or_none()

    authorization = request.headers.get("Authorization")
    if not authorization:
        if (
            mode == "new_devices_required"
            and allow_legacy
            and device is not None
            and device.legacy_enrollment_eligible
            and not device.credentials
        ):
            db.session.add(
                DeviceEnrollmentEvent(
                    device_id=device.id,
                    category="legacy_authentication_used",
                )
            )
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                _fail(device, None, "database_error")
            context = DeviceAuthenticationContext(device, None, True)
            g.device_authentication_context = context
            return context
        _fail(device, None, "missing_credential")

    assert authorization is not None
    credential_uuid = _parse_authorization(authorization)
    credential = db.session.execute(
        select(DeviceCredential).where(
            DeviceCredential.credential_uuid == credential_uuid
        )
    ).scalar_one_or_none()
    if credential is None or credential.status != "active":
        _fail(device, credential, "invalid_credential")
    assert credential is not None
    if device is None or credential.device_id != device.id:
        _fail(device, credential, "credential_device_mismatch")

    try:
        timestamp_text = _single_header("X-Device-Timestamp", 10)
        nonce_text = _single_header("X-Device-Nonce", 22)
        body_hash = _single_header("X-Device-Body-SHA256", 64)
        signature_text = _single_header("X-Device-Signature", 342)
        _parse_timestamp(timestamp_text)
        nonce = decode_base64url(nonce_text, decoded_length=16)
        raw_target = _raw_request_target()
        canonical_path, canonical_query = canonicalize_request_target(raw_target)
        _validate_query_names(canonical_query, allowed_query_names)
        actual_body_hash = hashlib.sha256(request.get_data(cache=True)).hexdigest()
        if not hmac.compare_digest(actual_body_hash, body_hash):
            raise DeviceCryptographyError("body digest mismatch")
        message = request_message(
            method=request.method.upper(),
            canonical_path=canonical_path,
            canonical_query=canonical_query,
            body_hash=body_hash,
            timestamp=timestamp_text,
            nonce=nonce_text,
            credential_uuid=str(credential.credential_uuid),
            device_uuid=str(device.device_uuid),
        )
        key = serialization.load_der_public_key(credential.public_key_der)
        if not isinstance(key, rsa.RSAPublicKey):
            raise DeviceCryptographyError("stored public key is invalid")
        signature = decode_base64url(signature_text, decoded_length=256)
        key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
    except (DeviceCryptographyError, InvalidSignature, ValueError, TypeError):
        _fail(device, credential, "invalid_signature")

    now = utc_now()
    nonce_record = DeviceRequestNonce(
        credential_id=credential.id,
        nonce_hash=hashlib.sha256(nonce).digest(),
        observed_at=now,
        expires_at=now
        + timedelta(seconds=current_app.config["DEVICE_AUTH_NONCE_TTL_SECONDS"]),
    )
    db.session.execute(
        delete(DeviceRequestNonce).where(DeviceRequestNonce.expires_at <= now)
    )
    credential.last_used_at = now
    db.session.add(nonce_record)
    db.session.add(
        DeviceEnrollmentEvent(
            device_id=device.id,
            credential_id=credential.id,
            category="authentication_succeeded",
            public_key_fingerprint=credential.public_key_fingerprint,
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        _fail(device, credential, "replayed_nonce")
    except SQLAlchemyError:
        db.session.rollback()
        _fail(device, credential, "database_error")
    context = DeviceAuthenticationContext(device, credential, False)
    g.device_authentication_context = context
    return context


def credential_rate_limit_key() -> str:
    context = getattr(g, "device_authentication_context", None)
    if context is None or context.credential is None:
        return f"legacy:{request.remote_addr or 'unknown'}"
    return f"credential:{context.credential.credential_uuid}"


def get_device_authentication_context() -> DeviceAuthenticationContext:
    return cast(DeviceAuthenticationContext, g.device_authentication_context)


def _parse_authorization(value: str) -> UUID:
    if len(value) != 53 or not value.startswith("DeviceCredential "):
        _fail(None, None, "invalid_authorization")
    credential_text = value.removeprefix("DeviceCredential ")
    try:
        credential_uuid = UUID(credential_text)
    except ValueError:
        _fail(None, None, "invalid_authorization")
    if str(credential_uuid) != credential_text or credential_uuid.version != 4:
        _fail(None, None, "invalid_authorization")
    return credential_uuid


def _single_header(name: str, exact_length: int) -> str:
    values = request.headers.getlist(name)
    if len(values) != 1:
        raise DeviceCryptographyError("missing or repeated header")
    value = values[0]
    if len(value) != exact_length or value != value.strip() or "," in value:
        raise DeviceCryptographyError("invalid header")
    return value


def _parse_timestamp(value: str) -> datetime:
    if (
        not value.isascii()
        or not value.isdigit()
        or (len(value) > 1 and value.startswith("0"))
    ):
        raise DeviceCryptographyError("invalid timestamp")
    timestamp = datetime.fromtimestamp(int(value), UTC)
    skew = timedelta(seconds=current_app.config["DEVICE_AUTH_CLOCK_SKEW_SECONDS"])
    if abs(utc_now() - timestamp) > skew:
        raise DeviceCryptographyError("stale timestamp")
    return timestamp


def _raw_request_target() -> str:
    raw_target = request.environ.get("RAW_URI") or request.environ.get("REQUEST_URI")
    if not isinstance(raw_target, str):
        if current_app.testing:
            raw_target = request.full_path.removesuffix("?")
        else:
            raise DeviceCryptographyError("raw request target unavailable")
    if raw_target.startswith("http://") or raw_target.startswith("https://"):
        raise DeviceCryptographyError("absolute request target")
    return raw_target


def _validate_query_names(query: str, allowed: frozenset[str]) -> None:
    names = {component.split("=", 1)[0] for component in query.split("&") if component}
    if not names.issubset(allowed):
        raise DeviceCryptographyError("unknown query parameter")


def _fail(
    device: Device | None,
    credential: DeviceCredential | None,
    failure_class: str,
) -> Never:
    try:
        db.session.add(
            DeviceEnrollmentEvent(
                device_id=device.id if device else None,
                credential_id=credential.id if credential else None,
                category="authentication_failed",
                failure_class=failure_class,
                public_key_fingerprint=(
                    credential.public_key_fingerprint if credential else None
                ),
            )
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
    raise DeviceAuthenticationFailed("device authentication failed")


def _failure_response() -> Response:
    response = jsonify({"error": "authentication_failed"})
    response.status_code = 401
    response.headers["Cache-Control"] = "no-store"
    return response


__all__ = [
    "DeviceAuthenticationContext",
    "DeviceAuthenticationFailed",
    "authenticate_device_request",
    "credential_rate_limit_key",
    "device_authentication_required",
    "get_device_authentication_context",
]
