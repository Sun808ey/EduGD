from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.device_cryptography import (
    DeviceCryptographyError,
    decode_base64url,
    encode_base64url,
    enrollment_message,
    rotation_message,
    validate_public_key,
    verify_signature,
)
from app.enrollment_schemas import DeviceEnrollmentData, RotationData, TokenIssueData
from app.extensions import db
from app.models import (
    Administrator,
    Device,
    DeviceCredential,
    DeviceEnrollmentEvent,
    EnrollmentToken,
    utc_now,
)


class EnrollmentFailed(RuntimeError):
    pass


class EnrollmentConflict(RuntimeError):
    pass


class EnrollmentDatabaseError(RuntimeError):
    pass


class EnrollmentNotFound(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token_uuid: str
    pairing_token: str
    expires_at: str
    bound_device_uuid: str | None


@dataclass(frozen=True, slots=True)
class EnrollmentResult:
    device_uuid: str
    credential_uuid: str
    credential_algorithm: str
    device_status: str
    server_time: str
    enrollment_event_uuid: str


def _pepper(version: int) -> bytes:
    configured_peppers = current_app.config.get("PAIRING_TOKEN_PEPPERS")
    value = None
    if isinstance(configured_peppers, dict):
        value = configured_peppers.get(version)
    if value is None and version == current_app.config["PAIRING_TOKEN_PEPPER_VERSION"]:
        value = current_app.config.get("PAIRING_TOKEN_PEPPER")
    if not isinstance(value, str) or len(value) < 32:
        raise EnrollmentDatabaseError("pairing token service is unavailable")
    return value.encode("utf-8")


def _token_verifier(token_uuid: str, secret: bytes, pepper_version: int) -> bytes:
    return hmac.new(
        _pepper(pepper_version),
        token_uuid.encode("ascii") + b"\x00" + secret,
        hashlib.sha256,
    ).digest()


def issue_enrollment_token(
    data: TokenIssueData,
    administrator: Administrator,
) -> IssuedToken:
    if not current_app.config["ENROLLMENT_ADMIN_ENABLED"]:
        raise EnrollmentConflict("enrollment administration is disabled")
    token_uuid = uuid4()
    secret = secrets.token_bytes(32)
    bound_device: Device | None = None
    if data.bound_device_uuid is not None:
        bound_device = db.session.execute(
            select(Device).where(Device.device_uuid == UUID(data.bound_device_uuid))
        ).scalar_one_or_none()
        if bound_device is None:
            raise EnrollmentNotFound("device not found")
    now = utc_now()
    expires_at = now + timedelta(
        seconds=current_app.config["ENROLLMENT_TOKEN_TTL_SECONDS"]
    )
    token = EnrollmentToken(
        token_uuid=token_uuid,
        verifier=_token_verifier(
            str(token_uuid),
            secret,
            current_app.config["PAIRING_TOKEN_PEPPER_VERSION"],
        ),
        pepper_version=current_app.config["PAIRING_TOKEN_PEPPER_VERSION"],
        bound_device_id=bound_device.id if bound_device else None,
        expires_at=expires_at,
        issued_by=str(administrator.administrator_uuid),
        reason=data.reason,
    )
    event = DeviceEnrollmentEvent(
        device_id=bound_device.id if bound_device else None,
        token_id=None,
        category="token_issued",
        administrator_subject=str(administrator.administrator_uuid),
        reason=data.reason,
    )
    try:
        db.session.add(token)
        db.session.flush()
        event.token_id = token.id
        db.session.add(event)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise EnrollmentDatabaseError("token issuance failed") from error
    return IssuedToken(
        str(token_uuid),
        f"{token_uuid}.{encode_base64url(secret)}",
        expires_at.isoformat().replace("+00:00", "Z"),
        str(bound_device.device_uuid) if bound_device else None,
    )


def revoke_enrollment_token(
    token_uuid: UUID,
    reason: str,
    administrator: Administrator,
) -> None:
    token = db.session.execute(
        select(EnrollmentToken)
        .where(EnrollmentToken.token_uuid == token_uuid)
        .with_for_update()
    ).scalar_one_or_none()
    if token is None:
        raise EnrollmentNotFound("enrollment token not found")
    if token.status != "active":
        raise EnrollmentConflict("enrollment token is not active")
    now = utc_now()
    token.status = "revoked"
    token.revoked_at = now
    token.revoked_by = str(administrator.administrator_uuid)
    token.revocation_reason = reason
    db.session.add(
        DeviceEnrollmentEvent(
            device_id=token.bound_device_id,
            token_id=token.id,
            category="token_revoked",
            administrator_subject=str(administrator.administrator_uuid),
            reason=reason,
        )
    )
    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise EnrollmentDatabaseError("token revocation failed") from error


def enroll_device(data: DeviceEnrollmentData) -> EnrollmentResult:
    token_uuid, secret = _parse_pairing_token(data.pairing_token)
    token = db.session.execute(
        select(EnrollmentToken)
        .where(EnrollmentToken.token_uuid == token_uuid)
        .with_for_update()
    ).scalar_one_or_none()
    if token is None:
        _record_failed_enrollment(None, None, "invalid_token")
    now = utc_now()
    assert token is not None
    if token.status != "active":
        _record_failed_enrollment(token, token.bound_device_id, "inactive_token")
    if _as_utc(token.expires_at) <= now:
        token.status = "expired"
        _record_failed_enrollment(token, token.bound_device_id, "expired_token")
    presented_verifier = _token_verifier(str(token_uuid), secret, token.pepper_version)
    if not hmac.compare_digest(token.verifier, presented_verifier):
        _record_failed_enrollment(token, token.bound_device_id, "invalid_token")

    device_uuid = UUID(data.device_uuid)
    device = db.session.execute(
        select(Device).where(Device.device_uuid == device_uuid).with_for_update()
    ).scalar_one_or_none()
    if token.bound_device_id is not None:
        if device is None or device.id != token.bound_device_id:
            _record_failed_enrollment(token, token.bound_device_id, "binding_mismatch")
    elif device is not None:
        raise EnrollmentConflict("existing device requires a bound enrollment token")

    if device is not None and any(
        credential.status == "active" for credential in device.credentials
    ):
        raise EnrollmentConflict("device already has an active credential")

    try:
        public_key = validate_public_key(data.credential.public_key)
        if data.credential.algorithm != "RSA_2048_SHA256":
            raise DeviceCryptographyError("unsupported credential algorithm")
        decode_base64url(data.credential.nonce, decoded_length=16)
        message = enrollment_message(
            device_uuid=data.device_uuid,
            token_uuid=str(token_uuid),
            algorithm=data.credential.algorithm,
            public_key_fingerprint=public_key.fingerprint,
            android_version=data.android_version,
            api_level=data.api_level,
            nonce=data.credential.nonce,
        )
        verify_signature(public_key.key, data.credential.proof, message)
    except DeviceCryptographyError:
        _record_failed_enrollment(token, token.bound_device_id, "invalid_proof")

    try:
        if device is None:
            device = Device(
                device_uuid=device_uuid,
                android_version=data.android_version,
                api_level=data.api_level,
                status="active",
                legacy_enrollment_eligible=False,
            )
            db.session.add(device)
            db.session.flush()
        else:
            if data.api_level < device.api_level:
                _record_failed_enrollment(token, device.id, "downgrade_rejected")
            device.android_version = data.android_version
            device.api_level = data.api_level

        credential = DeviceCredential(
            device_id=device.id,
            enrollment_token_id=token.id,
            algorithm=data.credential.algorithm,
            public_key_der=public_key.der,
            public_key_fingerprint=public_key.fingerprint,
            status="active",
        )
        db.session.add(credential)
        db.session.flush()
        token.status = "consumed"
        token.consumed_at = now
        token.consumed_by_device_id = device.id
        token_event = DeviceEnrollmentEvent(
            device_id=device.id,
            credential_id=credential.id,
            token_id=token.id,
            category="token_consumed",
            public_key_fingerprint=public_key.fingerprint,
        )
        enrollment_event = DeviceEnrollmentEvent(
            device_id=device.id,
            credential_id=credential.id,
            token_id=token.id,
            category="enrollment_succeeded",
            public_key_fingerprint=public_key.fingerprint,
        )
        db.session.add_all((token_event, enrollment_event))
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise EnrollmentDatabaseError("device enrollment failed") from error
    return EnrollmentResult(
        str(device.device_uuid),
        str(credential.credential_uuid),
        credential.algorithm,
        device.status,
        now.isoformat().replace("+00:00", "Z"),
        str(enrollment_event.event_uuid),
    )


def rotate_device_credential(
    current: DeviceCredential,
    data: RotationData,
) -> str:
    try:
        public_key = validate_public_key(data.public_key)
        if data.algorithm != "RSA_2048_SHA256":
            raise DeviceCryptographyError("unsupported algorithm")
        decode_base64url(data.nonce, decoded_length=16)
        message = rotation_message(
            device_uuid=str(current.device.device_uuid),
            current_credential_uuid=str(current.credential_uuid),
            algorithm=data.algorithm,
            public_key_fingerprint=public_key.fingerprint,
            nonce=data.nonce,
        )
        verify_signature(public_key.key, data.proof, message)
    except DeviceCryptographyError as error:
        raise EnrollmentFailed("credential rotation failed") from error
    try:
        now = utc_now()
        current.status = "superseded"
        current.superseded_at = now
        current.superseded_by_id = None
        db.session.flush()
        replacement = DeviceCredential(
            device_id=current.device_id,
            algorithm=data.algorithm,
            public_key_der=public_key.der,
            public_key_fingerprint=public_key.fingerprint,
            status="active",
        )
        db.session.add(replacement)
        db.session.flush()
        current.superseded_by_id = replacement.id
        db.session.add(
            DeviceEnrollmentEvent(
                device_id=current.device_id,
                credential_id=replacement.id,
                category="credential_rotated",
                public_key_fingerprint=public_key.fingerprint,
            )
        )
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise EnrollmentDatabaseError("credential rotation failed") from error
    return str(replacement.credential_uuid)


def revoke_device_credential(
    device_uuid: UUID,
    reason: str,
    administrator: Administrator,
) -> None:
    credential = db.session.execute(
        select(DeviceCredential)
        .join(Device, Device.id == DeviceCredential.device_id)
        .where(
            Device.device_uuid == device_uuid,
            DeviceCredential.status == "active",
        )
        .with_for_update()
    ).scalar_one_or_none()
    if credential is None:
        raise EnrollmentNotFound("active credential not found")
    now = utc_now()
    credential.status = "revoked"
    credential.revoked_at = now
    credential.revoked_by = str(administrator.administrator_uuid)
    credential.revocation_reason = reason
    db.session.add(
        DeviceEnrollmentEvent(
            device_id=credential.device_id,
            credential_id=credential.id,
            category="credential_revoked",
            administrator_subject=str(administrator.administrator_uuid),
            reason=reason,
            public_key_fingerprint=credential.public_key_fingerprint,
        )
    )
    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise EnrollmentDatabaseError("credential revocation failed") from error


def _parse_pairing_token(value: str) -> tuple[UUID, bytes]:
    if value.count(".") != 1:
        raise EnrollmentFailed("device enrollment failed")
    token_text, secret_text = value.split(".", 1)
    try:
        token_uuid = UUID(token_text)
        if str(token_uuid) != token_text or token_uuid.version != 4:
            raise ValueError
        secret = decode_base64url(secret_text, decoded_length=32)
    except (ValueError, DeviceCryptographyError) as error:
        raise EnrollmentFailed("device enrollment failed") from error
    return token_uuid, secret


def _record_failed_enrollment(
    token: EnrollmentToken | None,
    device_id: int | None,
    failure_class: str,
) -> None:
    if token is not None and token.status == "active":
        token.failed_attempts = min(token.failed_attempts + 1, 5)
        if token.failed_attempts >= 5:
            token.status = "locked"
    db.session.add(
        DeviceEnrollmentEvent(
            device_id=device_id,
            token_id=token.id if token else None,
            category="enrollment_failed",
            failure_class=failure_class,
        )
    )
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
    raise EnrollmentFailed("device enrollment failed")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "EnrollmentConflict",
    "EnrollmentDatabaseError",
    "EnrollmentFailed",
    "EnrollmentNotFound",
    "EnrollmentResult",
    "IssuedToken",
    "enroll_device",
    "issue_enrollment_token",
    "revoke_device_credential",
    "revoke_enrollment_token",
    "rotate_device_credential",
]
