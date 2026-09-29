from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import cast
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyRevision,
    PolicySynchronizationChainHead,
    PolicySynchronizationEvent,
    policy_revision_content_hash,
    utc_now,
    validate_policy_revision_payload,
)

MAX_CURRENT_VERSION = 2_147_483_647


class InvalidDeviceUUIDError(ValueError):
    def __init__(self) -> None:
        super().__init__("invalid device UUID")


class InvalidCurrentVersionError(ValueError):
    def __init__(self) -> None:
        super().__init__("current_version must be an integer from 0 to 2147483647")


class InvalidClientPolicyIdentityError(ValueError):
    def __init__(self) -> None:
        super().__init__("client policy identity must contain canonical UUIDv4 values")


class PolicySyncStateError(RuntimeError):
    outcome_category = "internal_error"
    operation = "error"

    def __init__(
        self,
        message: str,
        *,
        device_id: int | None = None,
        server_policy_version: int | None = None,
    ) -> None:
        super().__init__(message)
        self.device_id = device_id
        self.server_policy_version = server_policy_version


class DeviceNotFoundError(PolicySyncStateError, LookupError):
    outcome_category = "device_not_found"

    def __init__(self) -> None:
        super().__init__("device not found")


class DeviceBlockedError(PolicySyncStateError, PermissionError):
    outcome_category = "device_inactive"
    operation = "blocked"

    def __init__(self, device_id: int) -> None:
        super().__init__("device is not active", device_id=device_id)


class PolicyInactiveError(PolicySyncStateError):
    outcome_category = "policy_inactive"
    operation = "blocked"

    def __init__(self, device_id: int, server_policy_version: int) -> None:
        super().__init__(
            "assigned policy is not active",
            device_id=device_id,
            server_policy_version=server_policy_version,
        )


class PolicyRevokedError(PolicySyncStateError):
    outcome_category = "policy_revoked"
    operation = "blocked"

    def __init__(self, device_id: int, server_policy_version: int) -> None:
        super().__init__(
            "assigned policy is revoked",
            device_id=device_id,
            server_policy_version=server_policy_version,
        )


class AssignmentIntegrityError(PolicySyncStateError):
    outcome_category = "assignment_corruption"

    def __init__(self, device_id: int) -> None:
        super().__init__("policy assignment integrity failure", device_id=device_id)


class RevisionMismatchError(PolicySyncStateError):
    outcome_category = "revision_mismatch"

    def __init__(self, device_id: int, server_policy_version: int) -> None:
        super().__init__(
            "policy revision evidence mismatch",
            device_id=device_id,
            server_policy_version=server_policy_version,
        )


class SynchronizationAuditPersistenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedPolicyState:
    device: Device
    assignment: DevicePolicyAssignment | None
    revision: PolicyRevision | None
    policy: Policy | None


def get_policy_sync_payload(device_uuid: object) -> dict[str, object]:
    """Return the preserved legacy contract without mutating synchronization state."""
    canonical_uuid = _canonicalize_device_uuid(device_uuid)
    state = _resolve_policy_state(canonical_uuid)
    if state.revision is None or state.policy is None:
        return {
            "device_uuid": str(canonical_uuid),
            "policy": None,
            "policy_version": 0,
            "message": "no policy assigned",
        }
    return {
        "device_uuid": str(canonical_uuid),
        "policy": _legacy_policy_document(state.revision, state.policy),
    }


def get_version_aware_policy_sync_payload(
    device_uuid: object,
    current_version: object,
    current_policy_uuid: object = None,
    current_revision_uuid: object = None,
) -> dict[str, object]:
    canonical_uuid = _canonicalize_device_uuid(device_uuid)
    validated_version = _validate_current_version(current_version)
    client_policy_uuid, client_revision_uuid = _client_policy_identity(
        current_policy_uuid,
        current_revision_uuid,
    )
    state = _resolve_policy_state(canonical_uuid)

    if state.revision is None or state.policy is None:
        operation = (
            "no_change"
            if validated_version == 0
            and client_policy_uuid is None
            and client_revision_uuid is None
            else "clear"
        )
        return _operation_payload(canonical_uuid, operation, 0, None)

    revision = state.revision
    policy = state.policy
    if client_revision_uuid == revision.revision_uuid:
        operation = "no_change"
    elif (
        client_policy_uuid == policy.policy_uuid
        and validated_version > revision.version
    ):
        operation = "rollback"
    elif (
        client_policy_uuid is None
        and client_revision_uuid is None
        and validated_version == revision.version
    ):
        operation = "no_change"
    else:
        operation = "apply"
    return _operation_payload(
        canonical_uuid,
        operation,
        revision.version,
        _policy_document(revision, policy),
    )


def record_policy_sync_event(
    *,
    requested_device_uuid: str,
    reported_client_version: int | None,
    reported_policy_uuid: UUID | None,
    reported_revision_uuid: UUID | None,
    operation: str,
    outcome_category: str,
    server_policy_version: int | None,
    device_id: int | None,
    credential_id: int | None,
) -> PolicySynchronizationEvent:
    requested_at = utc_now()
    event_uuid = uuid4()
    pseudonym = _device_pseudonym(requested_device_uuid)
    try:
        if device_id is not None:
            db.session.execute(
                select(Device.id).where(Device.id == device_id).with_for_update()
            ).scalar_one()
        if db.session.get_bind().dialect.name == "postgresql":
            advisory_key = int.from_bytes(pseudonym[:8], "big", signed=True)
            db.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": advisory_key}
            )
        chain_head = db.session.execute(
            select(PolicySynchronizationChainHead)
            .where(
                PolicySynchronizationChainHead.requested_device_pseudonym == pseudonym
            )
            .with_for_update()
        ).scalar_one_or_none()
        previous_hash = chain_head.head_event_hash if chain_head is not None else None
        evidence = {
            "credential_id": credential_id,
            "device_id": device_id,
            "event_uuid": str(event_uuid),
            "operation": operation,
            "outcome_category": outcome_category,
            "previous_event_hash": previous_hash.hex() if previous_hash else None,
            "reported_client_version": reported_client_version,
            "reported_policy_uuid": (
                str(reported_policy_uuid) if reported_policy_uuid else None
            ),
            "reported_revision_uuid": (
                str(reported_revision_uuid) if reported_revision_uuid else None
            ),
            "requested_at": requested_at.isoformat(),
            "requested_device_pseudonym": pseudonym.hex(),
            "server_policy_version": server_policy_version,
        }
        event_hash = hashlib.sha256(
            json.dumps(
                evidence,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).digest()
        event = PolicySynchronizationEvent(
            event_uuid=event_uuid,
            device_id=device_id,
            credential_id=credential_id,
            requested_device_pseudonym=pseudonym,
            reported_client_version=reported_client_version,
            reported_policy_uuid=reported_policy_uuid,
            reported_revision_uuid=reported_revision_uuid,
            server_policy_version=server_policy_version,
            operation=operation,
            outcome_category=outcome_category,
            requested_at=requested_at,
            previous_event_hash=previous_hash,
            event_hash=event_hash,
        )
        db.session.add(event)
        if chain_head is None:
            db.session.add(
                PolicySynchronizationChainHead(
                    requested_device_pseudonym=pseudonym,
                    head_event_hash=event_hash,
                    updated_at=requested_at,
                )
            )
        else:
            chain_head.head_event_hash = event_hash
            chain_head.updated_at = requested_at
        db.session.commit()
        return event
    except SQLAlchemyError as error:
        db.session.rollback()
        raise SynchronizationAuditPersistenceError(
            "synchronization event could not be persisted"
        ) from error


def _resolve_policy_state(device_uuid: UUID) -> ResolvedPolicyState:
    with db.session.no_autoflush:
        device = db.session.execute(
            select(Device).where(Device.device_uuid == device_uuid)
        ).scalar_one_or_none()
        if device is None:
            raise DeviceNotFoundError()
        if device.status != "active":
            raise DeviceBlockedError(device.id)

        assignments = db.session.scalars(
            select(DevicePolicyAssignment)
            .where(
                DevicePolicyAssignment.device_id == device.id,
                DevicePolicyAssignment.status == "active",
            )
            .order_by(
                DevicePolicyAssignment.assigned_at.desc(),
                DevicePolicyAssignment.id.desc(),
            )
            .limit(2)
        ).all()
        if not assignments:
            return ResolvedPolicyState(device, None, None, None)
        if len(assignments) != 1:
            raise AssignmentIntegrityError(device.id)
        assignment = assignments[0]

        result = db.session.execute(
            select(PolicyRevision, Policy)
            .join(Policy, Policy.id == PolicyRevision.policy_id)
            .where(PolicyRevision.id == assignment.policy_revision_id)
        ).one_or_none()
        if result is None:
            raise AssignmentIntegrityError(device.id)
        revision, policy = result
        if policy.status == "revoked":
            raise PolicyRevokedError(device.id, revision.version)
        if policy.status != "active":
            raise PolicyInactiveError(device.id, revision.version)
        try:
            payload = validate_policy_revision_payload(revision.payload)
        except ValueError as error:
            raise RevisionMismatchError(device.id, revision.version) from error
        if not hmac.compare_digest(
            revision.content_hash,
            policy_revision_content_hash(payload),
        ):
            raise RevisionMismatchError(device.id, revision.version)
        return ResolvedPolicyState(device, assignment, revision, policy)


def _policy_document(
    revision: PolicyRevision,
    policy: Policy,
) -> dict[str, object]:
    payload = validate_policy_revision_payload(revision.payload)
    return {
        "policy_uuid": str(policy.policy_uuid),
        "policy_revision_uuid": str(revision.revision_uuid),
        "policy_version": revision.version,
        "blocked_apps": list(cast(list[str], payload["blocked_apps"])),
    }


def _legacy_policy_document(
    revision: PolicyRevision,
    policy: Policy,
) -> dict[str, object]:
    payload = validate_policy_revision_payload(revision.payload)
    return {
        "policy_uuid": str(policy.policy_uuid),
        "policy_version": revision.version,
        "blocked_apps": list(cast(list[str], payload["blocked_apps"])),
    }


def _operation_payload(
    device_uuid: UUID,
    operation: str,
    server_policy_version: int,
    policy: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "device_uuid": str(device_uuid),
        "operation": operation,
        "server_policy_version": server_policy_version,
        "policy": policy,
    }


def _canonicalize_device_uuid(device_uuid: object) -> UUID:
    try:
        return parse_canonical_uuid4(device_uuid)
    except ValueError as error:
        raise InvalidDeviceUUIDError() from error


def _validate_current_version(current_version: object) -> int:
    if (
        isinstance(current_version, bool)
        or not isinstance(current_version, int)
        or not 0 <= current_version <= MAX_CURRENT_VERSION
    ):
        raise InvalidCurrentVersionError()
    return current_version


def _client_policy_identity(
    policy_uuid: object,
    revision_uuid: object,
) -> tuple[UUID | None, UUID | None]:
    if policy_uuid is None and revision_uuid is None:
        return None, None
    if policy_uuid is None or revision_uuid is None:
        raise InvalidClientPolicyIdentityError()
    try:
        return _uuid4_value(policy_uuid), _uuid4_value(revision_uuid)
    except ValueError as error:
        raise InvalidClientPolicyIdentityError() from error


def _uuid4_value(value: object) -> UUID:
    if isinstance(value, UUID):
        if value.version != 4:
            raise ValueError("UUID must be version 4")
        return value
    return parse_canonical_uuid4(value)


def _device_pseudonym(device_uuid: str) -> bytes:
    key = current_app.config["POLICY_SYNC_AUDIT_KEY"]
    if not isinstance(key, str) or not key:
        raise RuntimeError("audit pseudonym key is unavailable")
    return hmac.new(
        key.encode("utf-8"),
        device_uuid.encode("utf-8"),
        hashlib.sha256,
    ).digest()


__all__ = [
    "AssignmentIntegrityError",
    "DeviceBlockedError",
    "DeviceNotFoundError",
    "InvalidClientPolicyIdentityError",
    "InvalidCurrentVersionError",
    "InvalidDeviceUUIDError",
    "MAX_CURRENT_VERSION",
    "PolicyInactiveError",
    "PolicyRevokedError",
    "PolicySyncStateError",
    "RevisionMismatchError",
    "SynchronizationAuditPersistenceError",
    "get_policy_sync_payload",
    "get_version_aware_policy_sync_payload",
    "record_policy_sync_event",
]
