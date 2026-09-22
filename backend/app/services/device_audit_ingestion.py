from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.device_audit_contract import DeviceAuditContractError, verify_audit_batch
from app.extensions import db
from app.models import (
    Device,
    DeviceAuditBatch,
    DeviceAuditChainHead,
    DeviceCredential,
    DeviceSecurityEvent,
)
from app.policy_contract import canonical_json_bytes


class DeviceAuditIngestionError(RuntimeError):
    pass


class DeviceAuditConflictError(DeviceAuditIngestionError):
    pass


class DeviceAuditPersistenceError(DeviceAuditIngestionError):
    pass


@dataclass(frozen=True, slots=True)
class DeviceAuditReceipt:
    batch_uuid: str
    accepted_through_sequence: int
    chain_head: str
    replayed: bool


def ingest_device_audit_batch(
    payload: object,
    *,
    device: Device,
    credential: DeviceCredential,
) -> DeviceAuditReceipt:
    if device.status != "active" or credential.status != "active":
        raise DeviceAuditConflictError("device audit upload is not available")
    if not isinstance(payload, dict):
        raise DeviceAuditContractError("invalid signed audit batch")

    content_hash = hashlib.sha256(canonical_json_bytes(payload)).digest()
    batch_uuid = _batch_uuid(payload)
    try:
        existing = db.session.execute(
            select(DeviceAuditBatch).where(DeviceAuditBatch.batch_uuid == batch_uuid)
        ).scalar_one_or_none()
        if existing is not None:
            if (
                existing.device_id != device.id
                or existing.credential_id != credential.id
                or existing.content_hash != content_hash
            ):
                raise DeviceAuditConflictError("batch UUID was already used")
            return _receipt(existing, replayed=True)

        head = db.session.execute(
            select(DeviceAuditChainHead)
            .where(DeviceAuditChainHead.device_id == device.id)
            .with_for_update()
        ).scalar_one_or_none()
        expected_previous = head.head_event_hash.hex() if head else None
        expected_sequence = head.last_sequence + 1 if head else 1
        public_key = serialization.load_der_public_key(credential.public_key_der)
        if not isinstance(public_key, (rsa.RSAPublicKey, ec.EllipticCurvePublicKey)):
            raise DeviceAuditContractError("unsupported device audit key")
        checked = verify_audit_batch(
            payload,
            public_key,
            expected_previous_head=expected_previous,
            expected_first_sequence=expected_sequence,
        )
        if checked["device_uuid"] != str(device.device_uuid):
            raise DeviceAuditContractError("audit batch device mismatch")
        if checked["credential_uuid"] != str(credential.credential_uuid):
            raise DeviceAuditContractError("audit batch credential mismatch")

        stored_batch = DeviceAuditBatch(
            batch_uuid=UUID(str(checked["batch_uuid"])),
            device_id=device.id,
            credential_id=credential.id,
            first_sequence=int(str(checked["first_sequence"])),
            last_sequence=int(str(checked["last_sequence"])),
            previous_head=_hex_bytes(checked["previous_head"]),
            final_head=_required_hex_bytes(checked["final_head"]),
            signature_algorithm=str(checked["signature_algorithm"]),
            signature=_decode_signature(payload.get("signature")),
            content_hash=content_hash,
        )
        db.session.add(stored_batch)
        db.session.flush()
        checked_events = checked["events"]
        if not isinstance(checked_events, list):
            raise DeviceAuditContractError("invalid audit events")
        for event in checked_events:
            assert isinstance(event, dict)
            db.session.add(
                DeviceSecurityEvent(
                    event_uuid=UUID(str(event["event_uuid"])),
                    batch_id=stored_batch.id,
                    device_id=device.id,
                    sequence=int(str(event["sequence"])),
                    occurred_at=_timestamp(str(event["occurred_at"])),
                    elapsed_realtime_ms=int(str(event["elapsed_realtime_ms"])),
                    boot_count=int(str(event["boot_count"])),
                    event_code=str(event["event_code"]),
                    outcome=str(event["outcome"]),
                    policy_uuid=_optional_uuid(event["policy_uuid"]),
                    revision_uuid=_optional_uuid(event["revision_uuid"]),
                    rule_id=str(event["rule_id"])
                    if event["rule_id"] is not None
                    else None,
                    event_metadata=dict(event["metadata"]),
                    previous_event_hash=_hex_bytes(event["previous_event_hash"]),
                    event_hash=_required_hex_bytes(event["event_hash"]),
                )
            )
        if head is None:
            head = DeviceAuditChainHead(device_id=device.id)
        head.last_sequence = stored_batch.last_sequence
        head.head_event_hash = stored_batch.final_head
        db.session.add(head)
        db.session.commit()
        return _receipt(stored_batch, replayed=False)
    except (DeviceAuditContractError, DeviceAuditConflictError):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise DeviceAuditConflictError(
            "audit batch conflicts with stored evidence"
        ) from error
    except (SQLAlchemyError, ValueError, TypeError) as error:
        db.session.rollback()
        raise DeviceAuditPersistenceError(
            "device audit batch could not be stored"
        ) from error


def _batch_uuid(payload: dict[object, object]) -> UUID:
    value = payload.get("batch_uuid")
    if not isinstance(value, str):
        raise DeviceAuditContractError("invalid batch_uuid")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise DeviceAuditContractError("invalid batch_uuid") from error
    if parsed.version != 4 or str(parsed) != value:
        raise DeviceAuditContractError("invalid batch_uuid")
    return parsed


def _receipt(batch: DeviceAuditBatch, *, replayed: bool) -> DeviceAuditReceipt:
    return DeviceAuditReceipt(
        batch_uuid=str(batch.batch_uuid),
        accepted_through_sequence=batch.last_sequence,
        chain_head=batch.final_head.hex(),
        replayed=replayed,
    )


def _decode_signature(value: object) -> bytes:
    if not isinstance(value, str):
        raise DeviceAuditContractError("invalid audit batch signature")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as error:
        raise DeviceAuditContractError("invalid audit batch signature") from error
    if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != value:
        raise DeviceAuditContractError("invalid audit batch signature")
    return decoded


def _hex_bytes(value: object) -> bytes | None:
    return None if value is None else _required_hex_bytes(value)


def _required_hex_bytes(value: object) -> bytes:
    if not isinstance(value, str):
        raise DeviceAuditContractError("invalid audit hash")
    return bytes.fromhex(value)


def _optional_uuid(value: object) -> UUID | None:
    return None if value is None else UUID(str(value))


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00").astimezone(UTC)


__all__ = [
    "DeviceAuditConflictError",
    "DeviceAuditIngestionError",
    "DeviceAuditPersistenceError",
    "DeviceAuditReceipt",
    "ingest_device_audit_batch",
]
