from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.device_status_contract import (
    DeviceStatusContractError,
    validate_check_in,
    validate_policy_acknowledgement,
)
from app.extensions import db
from app.models import (
    Device,
    DeviceCheckIn,
    DeviceComplianceState,
    DeviceCredential,
    DevicePolicyState,
    Policy,
    PolicyApplicationEvent,
    PolicyRevision,
    utc_now,
)
from app.policy_contract import canonical_json_bytes


class DeviceStatusConflictError(RuntimeError):
    pass


class DeviceStatusPersistenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeviceStatusReceipt:
    record_uuid: str
    replayed: bool


def record_check_in(
    payload: object, *, device: Device, credential: DeviceCredential
) -> DeviceStatusReceipt:
    checked = validate_check_in(payload)
    _active(device, credential)
    if (
        checked["api_level"] != device.api_level
        or checked["android_version"] != device.android_version
    ):
        raise DeviceStatusConflictError(
            "reported Android identity does not match enrollment"
        )
    content_hash = hashlib.sha256(canonical_json_bytes(checked)).digest()
    check_in_uuid = UUID(str(checked["check_in_uuid"]))
    try:
        existing = db.session.execute(
            select(DeviceCheckIn).where(DeviceCheckIn.check_in_uuid == check_in_uuid)
        ).scalar_one_or_none()
        if existing is not None:
            _exact_replay(
                existing.device_id,
                existing.credential_id,
                existing.content_hash,
                device,
                credential,
                content_hash,
            )
            return DeviceStatusReceipt(str(existing.check_in_uuid), True)
        received_at = utc_now()
        capabilities = checked["capabilities"]
        assert isinstance(capabilities, list)
        check_in = DeviceCheckIn(
            check_in_uuid=check_in_uuid,
            device_id=device.id,
            credential_id=credential.id,
            observed_at=_timestamp(checked["observed_at"]),
            received_at=received_at,
            elapsed_realtime_ms=int(str(checked["elapsed_realtime_ms"])),
            boot_count=int(str(checked["boot_count"])),
            dpc_version=int(str(checked["dpc_version"])),
            android_version=str(checked["android_version"]),
            api_level=int(str(checked["api_level"])),
            security_patch=date.fromisoformat(str(checked["security_patch"])),
            capabilities=[str(capability) for capability in capabilities],
            current_policy_uuid=_optional_uuid(checked["current_policy_uuid"]),
            current_revision_uuid=_optional_uuid(checked["current_revision_uuid"]),
            policy_status=str(checked["policy_status"]),
            enforcement_healthy=bool(checked["enforcement_healthy"]),
            queued_event_count=int(str(checked["queued_event_count"])),
            content_hash=content_hash,
        )
        db.session.add(check_in)
        db.session.flush()
        state = db.session.execute(
            select(DeviceComplianceState)
            .where(DeviceComplianceState.device_id == device.id)
            .with_for_update()
        ).scalar_one_or_none()
        if state is None:
            state = DeviceComplianceState(device_id=device.id)
        if state.last_observed_at is None or _utc(check_in.observed_at) >= _utc(
            state.last_observed_at
        ):
            state.last_check_in_id = check_in.id
            state.last_observed_at = check_in.observed_at
            state.last_received_at = received_at
            state.last_boot_count = check_in.boot_count
            state.dpc_version = check_in.dpc_version
            state.android_version = check_in.android_version
            state.api_level = check_in.api_level
            state.security_patch = check_in.security_patch
            state.capabilities = list(check_in.capabilities)
            state.current_policy_uuid = check_in.current_policy_uuid
            state.current_revision_uuid = check_in.current_revision_uuid
            state.policy_status = check_in.policy_status
            state.enforcement_healthy = check_in.enforcement_healthy
            state.queued_event_count = check_in.queued_event_count
            db.session.add(state)
        device.last_sync_at = received_at
        db.session.commit()
        return DeviceStatusReceipt(str(check_in.check_in_uuid), False)
    except (DeviceStatusContractError, DeviceStatusConflictError):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise DeviceStatusConflictError(
            "check-in conflicts with stored state"
        ) from error
    except (SQLAlchemyError, ValueError, TypeError) as error:
        db.session.rollback()
        raise DeviceStatusPersistenceError("check-in could not be stored") from error


def record_policy_acknowledgement(
    payload: object, *, device: Device, credential: DeviceCredential
) -> DeviceStatusReceipt:
    checked = validate_policy_acknowledgement(payload)
    _active(device, credential)
    content_hash = hashlib.sha256(canonical_json_bytes(checked)).digest()
    acknowledgement_uuid = UUID(str(checked["acknowledgement_uuid"]))
    try:
        existing = db.session.execute(
            select(PolicyApplicationEvent).where(
                PolicyApplicationEvent.acknowledgement_uuid == acknowledgement_uuid
            )
        ).scalar_one_or_none()
        if existing is not None:
            _exact_replay(
                existing.device_id,
                existing.credential_id,
                existing.content_hash,
                device,
                credential,
                content_hash,
            )
            return DeviceStatusReceipt(str(existing.acknowledgement_uuid), True)
        policy_uuid = _optional_uuid(checked["policy_uuid"])
        revision_uuid = _optional_uuid(checked["revision_uuid"])
        if policy_uuid is not None:
            known = db.session.execute(
                select(PolicyRevision.id)
                .join(Policy, Policy.id == PolicyRevision.policy_id)
                .where(
                    Policy.policy_uuid == policy_uuid,
                    PolicyRevision.revision_uuid == revision_uuid,
                )
            ).scalar_one_or_none()
            if known is None:
                raise DeviceStatusConflictError(
                    "acknowledged policy revision is unknown"
                )
        received_at = utc_now()
        application_event = PolicyApplicationEvent(
            acknowledgement_uuid=acknowledgement_uuid,
            device_id=device.id,
            credential_id=credential.id,
            observed_at=_timestamp(checked["observed_at"]),
            received_at=received_at,
            elapsed_realtime_ms=int(str(checked["elapsed_realtime_ms"])),
            boot_count=int(str(checked["boot_count"])),
            policy_uuid=policy_uuid,
            revision_uuid=revision_uuid,
            outcome=str(checked["outcome"]),
            error_code=str(checked["error_code"])
            if checked["error_code"] is not None
            else None,
            content_hash=content_hash,
        )
        db.session.add(application_event)
        db.session.flush()
        state = db.session.execute(
            select(DevicePolicyState)
            .where(DevicePolicyState.device_id == device.id)
            .with_for_update()
        ).scalar_one_or_none()
        if state is None:
            state = DevicePolicyState(device_id=device.id)
        if state.observed_at is None or _utc(application_event.observed_at) >= _utc(
            state.observed_at
        ):
            state.last_event_id = application_event.id
            state.policy_uuid = application_event.policy_uuid
            state.revision_uuid = application_event.revision_uuid
            state.outcome = application_event.outcome
            state.error_code = application_event.error_code
            state.observed_at = application_event.observed_at
            state.received_at = received_at
            db.session.add(state)
        db.session.commit()
        return DeviceStatusReceipt(str(application_event.acknowledgement_uuid), False)
    except (DeviceStatusContractError, DeviceStatusConflictError):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise DeviceStatusConflictError(
            "acknowledgement conflicts with stored state"
        ) from error
    except (SQLAlchemyError, ValueError, TypeError) as error:
        db.session.rollback()
        raise DeviceStatusPersistenceError(
            "acknowledgement could not be stored"
        ) from error


def _active(device: Device, credential: DeviceCredential) -> None:
    if device.status != "active" or credential.status != "active":
        raise DeviceStatusConflictError("device status reporting is not available")


def _exact_replay(
    device_id: int,
    credential_id: int,
    stored_hash: bytes,
    device: Device,
    credential: DeviceCredential,
    content_hash: bytes,
) -> None:
    if (
        device_id != device.id
        or credential_id != credential.id
        or stored_hash != content_hash
    ):
        raise DeviceStatusConflictError("record UUID was already used")


def _optional_uuid(value: object) -> UUID | None:
    return None if value is None else UUID(str(value))


def _timestamp(value: object) -> datetime:
    return datetime.fromisoformat(str(value).removesuffix("Z") + "+00:00").astimezone(
        UTC
    )


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


__all__ = [
    "DeviceStatusConflictError",
    "DeviceStatusPersistenceError",
    "DeviceStatusReceipt",
    "record_check_in",
    "record_policy_acknowledgement",
]
