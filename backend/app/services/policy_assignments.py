import hashlib
import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    Administrator,
    AdministratorPermission,
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyAssignmentChainHead,
    PolicyAssignmentEvent,
    PolicyRevision,
    utc_now,
)


class InvalidPolicyAssignmentError(ValueError):
    pass


class PolicyAssignmentNotFoundError(LookupError):
    pass


class PolicyAssignmentForbiddenError(PermissionError):
    pass


class PolicyAssignmentConflictError(RuntimeError):
    pass


class PolicyAssignmentPersistenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PolicyAssignmentResult:
    assignment: DevicePolicyAssignment
    replaced: bool


@dataclass(frozen=True, slots=True)
class PolicyClearResult:
    cleared_assignment: DevicePolicyAssignment
    event: PolicyAssignmentEvent


def replace_policy_assignment(
    device_uuid: object,
    policy_revision_uuid: object,
    administrator_uuid: object,
    reason: object,
) -> PolicyAssignmentResult:
    canonical_device_uuid = _parse_uuid(device_uuid, "device_uuid")
    canonical_revision_uuid = _parse_uuid(
        policy_revision_uuid,
        "policy_revision_uuid",
    )
    canonical_administrator_uuid = _parse_uuid(
        administrator_uuid,
        "administrator_uuid",
    )
    validated_reason = _reason(reason)

    try:
        administrator = db.session.execute(
            select(Administrator)
            .join(
                AdministratorPermission,
                AdministratorPermission.administrator_id == Administrator.id,
            )
            .where(
                Administrator.administrator_uuid == canonical_administrator_uuid,
                Administrator.status == "active",
                AdministratorPermission.permission == "policy.assign",
            )
        ).scalar_one_or_none()
        if administrator is None:
            raise PolicyAssignmentForbiddenError(
                "administrator is not authorized to assign policy revisions"
            )

        device = db.session.execute(
            select(Device)
            .where(Device.device_uuid == canonical_device_uuid)
            .with_for_update()
        ).scalar_one_or_none()
        if device is None:
            raise PolicyAssignmentNotFoundError("device not found")
        if device.status != "active":
            raise PolicyAssignmentConflictError("device is not active")

        revision = db.session.execute(
            select(PolicyRevision)
            .join(Policy, Policy.id == PolicyRevision.policy_id)
            .where(
                PolicyRevision.revision_uuid == canonical_revision_uuid,
                Policy.status == "active",
            )
        ).scalar_one_or_none()
        if revision is None:
            raise PolicyAssignmentNotFoundError("active policy revision not found")

        current = db.session.execute(
            select(DevicePolicyAssignment)
            .where(
                DevicePolicyAssignment.device_id == device.id,
                DevicePolicyAssignment.status == "active",
            )
            .with_for_update()
        ).scalar_one_or_none()
        if current is not None and current.policy_revision_id == revision.id:
            db.session.commit()
            return PolicyAssignmentResult(current, replaced=False)

        now = utc_now()
        if current is not None:
            current.status = "superseded"
            current.superseded_at = now
            db.session.flush()

        assignment = DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=revision.id,
            assigned_by_administrator_id=administrator.id,
            trusted_operator_subject=None,
            reason=validated_reason,
            status="active",
            assigned_at=now,
        )
        db.session.add(assignment)
        db.session.flush()
        _append_assignment_event(
            device_id=device.id,
            administrator_id=administrator.id,
            operation="replace" if current is not None else "assign",
            reason=validated_reason,
            assignment_id=assignment.id,
            previous_assignment_id=current.id if current is not None else None,
        )
        db.session.commit()
        return PolicyAssignmentResult(assignment, replaced=current is not None)
    except (
        PolicyAssignmentNotFoundError,
        PolicyAssignmentForbiddenError,
        PolicyAssignmentConflictError,
    ):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise PolicyAssignmentConflictError(
            "policy assignment conflicted with current database state"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise PolicyAssignmentPersistenceError(
            "policy assignment could not be persisted"
        ) from error


def clear_policy_assignment(
    device_uuid: object,
    administrator_uuid: object,
    reason: object,
) -> PolicyClearResult:
    canonical_device_uuid = _parse_uuid(device_uuid, "device_uuid")
    canonical_administrator_uuid = _parse_uuid(administrator_uuid, "administrator_uuid")
    validated_reason = _reason(reason)
    try:
        administrator = _authorized_administrator(canonical_administrator_uuid)
        device = db.session.execute(
            select(Device)
            .where(Device.device_uuid == canonical_device_uuid)
            .with_for_update()
        ).scalar_one_or_none()
        if device is None:
            raise PolicyAssignmentNotFoundError("device not found")
        if device.status != "active":
            raise PolicyAssignmentConflictError("device is not active")
        current = db.session.execute(
            select(DevicePolicyAssignment)
            .where(
                DevicePolicyAssignment.device_id == device.id,
                DevicePolicyAssignment.status == "active",
            )
            .with_for_update()
        ).scalar_one_or_none()
        if current is None:
            raise PolicyAssignmentConflictError(
                "device has no active policy assignment"
            )
        current.status = "superseded"
        current.superseded_at = utc_now()
        db.session.flush()
        event = _append_assignment_event(
            device_id=device.id,
            administrator_id=administrator.id,
            operation="clear",
            reason=validated_reason,
            assignment_id=None,
            previous_assignment_id=current.id,
        )
        db.session.commit()
        return PolicyClearResult(current, event)
    except (
        PolicyAssignmentNotFoundError,
        PolicyAssignmentForbiddenError,
        PolicyAssignmentConflictError,
    ):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise PolicyAssignmentConflictError(
            "policy clear conflicted with current database state"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise PolicyAssignmentPersistenceError(
            "policy clear could not be persisted"
        ) from error


def _authorized_administrator(administrator_uuid: UUID) -> Administrator:
    administrator = db.session.execute(
        select(Administrator)
        .join(
            AdministratorPermission,
            AdministratorPermission.administrator_id == Administrator.id,
        )
        .where(
            Administrator.administrator_uuid == administrator_uuid,
            Administrator.status == "active",
            AdministratorPermission.permission == "policy.assign",
        )
    ).scalar_one_or_none()
    if administrator is None:
        raise PolicyAssignmentForbiddenError(
            "administrator is not authorized to assign policy revisions"
        )
    return administrator


def _append_assignment_event(
    *,
    device_id: int,
    administrator_id: int,
    operation: str,
    reason: str,
    assignment_id: int | None,
    previous_assignment_id: int | None,
) -> PolicyAssignmentEvent:
    head = db.session.execute(
        select(PolicyAssignmentChainHead)
        .where(PolicyAssignmentChainHead.device_id == device_id)
        .with_for_update()
    ).scalar_one_or_none()
    previous_hash = head.head_event_hash if head is not None else None
    event_uuid = uuid4()
    created_at = utc_now()
    evidence = {
        "administrator_id": administrator_id,
        "assignment_id": assignment_id,
        "created_at": created_at.isoformat(),
        "device_id": device_id,
        "event_uuid": str(event_uuid),
        "operation": operation,
        "previous_assignment_id": previous_assignment_id,
        "previous_event_hash": previous_hash.hex() if previous_hash else None,
        "reason": reason,
    }
    event_hash = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).digest()
    event = PolicyAssignmentEvent(
        event_uuid=event_uuid,
        device_id=device_id,
        assignment_id=assignment_id,
        previous_assignment_id=previous_assignment_id,
        administrator_id=administrator_id,
        operation=operation,
        reason=reason,
        created_at=created_at,
        previous_event_hash=previous_hash,
        event_hash=event_hash,
    )
    db.session.add(event)
    if head is None:
        db.session.add(
            PolicyAssignmentChainHead(device_id=device_id, head_event_hash=event_hash)
        )
    else:
        head.head_event_hash = event_hash
        head.updated_at = created_at
    return event


def _parse_uuid(value: object, field: str) -> UUID:
    try:
        return parse_canonical_uuid4(value)
    except ValueError as error:
        raise InvalidPolicyAssignmentError(f"invalid {field}") from error


def _reason(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 512
        or not value.isprintable()
    ):
        raise InvalidPolicyAssignmentError(
            "reason must contain 1 to 512 printable characters"
        )
    return value


__all__ = [
    "InvalidPolicyAssignmentError",
    "PolicyAssignmentConflictError",
    "PolicyAssignmentForbiddenError",
    "PolicyAssignmentNotFoundError",
    "PolicyAssignmentPersistenceError",
    "PolicyAssignmentResult",
    "PolicyClearResult",
    "clear_policy_assignment",
    "replace_policy_assignment",
]
