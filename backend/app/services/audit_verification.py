import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import select

from app.extensions import db
from app.models import (
    PolicyAssignmentChainHead,
    PolicyAssignmentEvent,
    PolicySynchronizationChainHead,
    PolicySynchronizationEvent,
)


class AuditChainVerificationError(RuntimeError):
    pass


def verify_policy_assignment_chain(device_id: int) -> None:
    events = db.session.scalars(
        select(PolicyAssignmentEvent)
        .where(PolicyAssignmentEvent.device_id == device_id)
        .order_by(PolicyAssignmentEvent.created_at, PolicyAssignmentEvent.id)
    ).all()
    expected_previous: bytes | None = None
    for event in events:
        if event.previous_event_hash != expected_previous:
            raise AuditChainVerificationError("assignment audit predecessor mismatch")
        evidence = {
            "administrator_id": event.administrator_id,
            "assignment_id": event.assignment_id,
            "created_at": _canonical_time(event.created_at),
            "device_id": event.device_id,
            "event_uuid": str(event.event_uuid),
            "operation": event.operation,
            "previous_assignment_id": event.previous_assignment_id,
            "previous_event_hash": expected_previous.hex()
            if expected_previous
            else None,
            "reason": event.reason,
        }
        expected_hash = _hash(evidence)
        if not hmac.compare_digest(event.event_hash, expected_hash):
            raise AuditChainVerificationError("assignment audit hash mismatch")
        expected_previous = event.event_hash
    head = db.session.get(PolicyAssignmentChainHead, device_id)
    _verify_head(
        head.head_event_hash if head else None, expected_previous, bool(events)
    )


def verify_policy_synchronization_chain(pseudonym: bytes) -> None:
    events = db.session.scalars(
        select(PolicySynchronizationEvent)
        .where(PolicySynchronizationEvent.requested_device_pseudonym == pseudonym)
        .order_by(
            PolicySynchronizationEvent.requested_at, PolicySynchronizationEvent.id
        )
    ).all()
    expected_previous: bytes | None = None
    for event in events:
        if event.previous_event_hash != expected_previous:
            raise AuditChainVerificationError(
                "synchronization audit predecessor mismatch"
            )
        evidence = {
            "credential_id": event.credential_id,
            "device_id": event.device_id,
            "event_uuid": str(event.event_uuid),
            "operation": event.operation,
            "outcome_category": event.outcome_category,
            "previous_event_hash": expected_previous.hex()
            if expected_previous
            else None,
            "reported_client_version": event.reported_client_version,
            "reported_policy_uuid": str(event.reported_policy_uuid)
            if event.reported_policy_uuid
            else None,
            "reported_revision_uuid": str(event.reported_revision_uuid)
            if event.reported_revision_uuid
            else None,
            "requested_at": _canonical_time(event.requested_at),
            "requested_device_pseudonym": pseudonym.hex(),
            "server_policy_version": event.server_policy_version,
        }
        expected_hash = _hash(evidence)
        if not hmac.compare_digest(event.event_hash, expected_hash):
            raise AuditChainVerificationError("synchronization audit hash mismatch")
        expected_previous = event.event_hash
    head = db.session.get(PolicySynchronizationChainHead, pseudonym)
    _verify_head(
        head.head_event_hash if head else None, expected_previous, bool(events)
    )


def _canonical_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _hash(evidence: Mapping[str, object]) -> bytes:
    return hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).digest()


def _verify_head(
    actual: bytes | None, expected: bytes | None, has_events: bool
) -> None:
    if has_events and actual != expected:
        raise AuditChainVerificationError("audit chain head mismatch")
    if not has_events and actual is not None:
        raise AuditChainVerificationError("orphaned audit chain head")


__all__ = [
    "AuditChainVerificationError",
    "verify_policy_assignment_chain",
    "verify_policy_synchronization_chain",
]
