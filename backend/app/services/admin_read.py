from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.admin_api import Pagination, isoformat_utc, pagination_payload
from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    ADMINISTRATOR_AUTHENTICATION_EVENT_CATEGORIES,
    DEVICE_ENROLLMENT_EVENT_CATEGORIES,
    POLICY_ASSIGNMENT_OPERATIONS,
    POLICY_SYNC_OPERATIONS,
    Administrator,
    AdministratorAuthenticationEvent,
    Device,
    DeviceAssetChangeEvent,
    DeviceComplianceState,
    DeviceEnrollmentEvent,
    DevicePolicyAssignment,
    EnrollmentToken,
    Incident,
    Policy,
    PolicyAssignmentEvent,
    PolicyRevision,
    PolicySynchronizationEvent,
)


class AdminReadNotFoundError(LookupError):
    pass


class AdminReadPersistenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PageResult:
    items: list[dict[str, object]]
    pagination: dict[str, int | bool]


def list_devices(
    pagination: Pagination,
    *,
    status: str | None = None,
) -> PageResult:
    statement = select(Device).order_by(Device.registered_at.desc(), Device.id.desc())
    count_statement: Select[tuple[int]] = select(func.count()).select_from(Device)
    if status is not None:
        statement = statement.where(Device.status == status)
        count_statement = count_statement.where(Device.status == status)
    try:
        total = int(db.session.scalar(count_statement) or 0)
        devices = db.session.scalars(
            statement.offset(pagination.offset).limit(pagination.per_page)
        ).all()
        return PageResult(
            [_device_summary(device) for device in devices],
            pagination_payload(pagination, total=total),
        )
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError("device list could not be loaded") from error


def get_device(device_uuid: object) -> dict[str, object]:
    canonical_uuid = _uuid(device_uuid)
    try:
        device = db.session.scalars(
            select(Device).where(Device.device_uuid == canonical_uuid)
        ).one_or_none()
        if device is None:
            raise AdminReadNotFoundError("device not found")
        return _device_detail(device)
    except AdminReadNotFoundError:
        raise
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError("device detail could not be loaded") from error


def get_device_policy_assignment(device_uuid: object) -> dict[str, object]:
    canonical_uuid = _uuid(device_uuid)
    try:
        device = db.session.scalars(
            select(Device).where(Device.device_uuid == canonical_uuid)
        ).one_or_none()
        if device is None:
            raise AdminReadNotFoundError("device not found")
        assignment = _active_assignment(device.id)
        return {
            "device_uuid": str(device.device_uuid),
            "assignment": _assignment_summary(assignment) if assignment else None,
        }
    except AdminReadNotFoundError:
        raise
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError("assignment could not be loaded") from error


def list_policies(
    pagination: Pagination,
    *,
    status: str | None = None,
) -> PageResult:
    statement = select(Policy).order_by(Policy.updated_at.desc(), Policy.id.desc())
    count_statement: Select[tuple[int]] = select(func.count()).select_from(Policy)
    if status is not None:
        statement = statement.where(Policy.status == status)
        count_statement = count_statement.where(Policy.status == status)
    try:
        total = int(db.session.scalar(count_statement) or 0)
        policies = db.session.scalars(
            statement.offset(pagination.offset).limit(pagination.per_page)
        ).all()
        return PageResult(
            [_policy_summary(policy) for policy in policies],
            pagination_payload(pagination, total=total),
        )
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError("policy list could not be loaded") from error


def get_policy(policy_uuid: object) -> dict[str, object]:
    canonical_uuid = _uuid(policy_uuid)
    try:
        policy = db.session.scalars(
            select(Policy).where(Policy.policy_uuid == canonical_uuid)
        ).one_or_none()
        if policy is None:
            raise AdminReadNotFoundError("policy not found")
        return _policy_detail(policy)
    except AdminReadNotFoundError:
        raise
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError("policy detail could not be loaded") from error


def list_policy_revisions(
    policy_uuid: object,
    pagination: Pagination,
) -> PageResult:
    canonical_uuid = _uuid(policy_uuid)
    try:
        policy = db.session.scalars(
            select(Policy).where(Policy.policy_uuid == canonical_uuid)
        ).one_or_none()
        if policy is None:
            raise AdminReadNotFoundError("policy not found")
        total = int(
            db.session.scalar(
                select(func.count())
                .select_from(PolicyRevision)
                .where(PolicyRevision.policy_id == policy.id)
            )
            or 0
        )
        revisions = db.session.scalars(
            select(PolicyRevision)
            .where(PolicyRevision.policy_id == policy.id)
            .order_by(PolicyRevision.version.desc())
            .offset(pagination.offset)
            .limit(pagination.per_page)
        ).all()
        return PageResult(
            [_revision_summary(revision) for revision in revisions],
            pagination_payload(pagination, total=total),
        )
    except AdminReadNotFoundError:
        raise
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError(
            "policy revisions could not be loaded"
        ) from error


def list_enrollment_tokens(
    pagination: Pagination,
    *,
    status: str | None = None,
) -> PageResult:
    statement = select(EnrollmentToken).order_by(
        EnrollmentToken.created_at.desc(), EnrollmentToken.id.desc()
    )
    count_statement: Select[tuple[int]] = select(func.count()).select_from(
        EnrollmentToken
    )
    if status is not None:
        statement = statement.where(EnrollmentToken.status == status)
        count_statement = count_statement.where(EnrollmentToken.status == status)
    try:
        total = int(db.session.scalar(count_statement) or 0)
        tokens = db.session.scalars(
            statement.offset(pagination.offset).limit(pagination.per_page)
        ).all()
        return PageResult(
            [_enrollment_token_summary(token) for token in tokens],
            pagination_payload(pagination, total=total),
        )
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError(
            "enrollment tokens could not be loaded"
        ) from error


def list_audit_events(
    pagination: Pagination,
    *,
    event_type: str | None = None,
) -> PageResult:
    loaders = {
        "administrator_authentication": _administrator_authentication_events,
        "device_enrollment": _device_enrollment_events,
        "policy_assignment": _policy_assignment_events,
        "policy_synchronization": _policy_synchronization_events,
        "incident": _incident_events,
        "device_asset": _device_asset_events,
    }
    selected_loaders = (
        [loaders[event_type]] if event_type is not None else list(loaders.values())
    )
    try:
        events: list[dict[str, object]] = []
        for loader in selected_loaders:
            events.extend(loader(pagination.offset + pagination.per_page))
        events.sort(key=lambda item: str(item["occurred_at"]), reverse=True)
        page_items = events[pagination.offset : pagination.offset + pagination.per_page]
        return PageResult(
            page_items,
            pagination_payload(pagination, total=len(events)),
        )
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError("audit events could not be loaded") from error


def list_policy_changes(pagination: Pagination) -> PageResult:
    statement = select(PolicyAssignmentEvent).order_by(
        PolicyAssignmentEvent.created_at.desc(), PolicyAssignmentEvent.id.desc()
    )
    count_statement = select(func.count()).select_from(PolicyAssignmentEvent)
    try:
        total = int(db.session.scalar(count_statement) or 0)
        events = db.session.scalars(
            statement.offset(pagination.offset).limit(pagination.per_page)
        ).all()
        return PageResult(
            [_policy_change_summary(event) for event in events],
            pagination_payload(pagination, total=total),
        )
    except SQLAlchemyError as error:
        raise AdminReadPersistenceError("policy changes could not be loaded") from error


def _device_summary(device: Device) -> dict[str, object]:
    assignment = _active_assignment(device.id)
    state = db.session.get(DeviceComplianceState, device.id)
    connection_review_after_days = _connection_review_threshold(assignment)
    enforcement_status = "NOT_REPORTED"
    failed_controls: list[str] = []
    if state is not None:
        expected = assignment is not None and (
            state.current_policy_uuid == assignment.policy_revision.policy.policy_uuid
            and state.current_revision_uuid == assignment.policy_revision.revision_uuid
        )
        if (
            state.enforcement_healthy
            and state.policy_status in {"verified", "applied"}
            and expected
        ):
            enforcement_status = "COMPLIANT"
        else:
            enforcement_status = "PARTIALLY_COMPLIANT"
            if not state.enforcement_healthy:
                failed_controls.append("DPC enforcement health check failed")
            if assignment is None:
                failed_controls.append("No active policy assignment")
            if not expected:
                failed_controls.append(
                    "Reported policy revision differs from assigned policy"
                )
            if state.policy_status not in {"verified", "applied"}:
                failed_controls.append(f"Policy status: {state.policy_status}")
    last_sync_at = device.last_sync_at
    if last_sync_at is None:
        connection_status = "OFFLINE"
        connection_review = True
    else:
        if last_sync_at.tzinfo is None:
            last_sync_at = last_sync_at.replace(tzinfo=UTC)
        connection_status = (
            "OFFLINE"
            if (datetime.now(UTC) - last_sync_at).total_seconds() > 24 * 60 * 60
            else "ONLINE"
        )
        connection_review = (
            datetime.now(UTC) - last_sync_at
        ).total_seconds() > connection_review_after_days * 24 * 60 * 60
    return {
        "device_uuid": str(device.device_uuid),
        "android_version": device.android_version,
        "api_level": device.api_level,
        "status": device.status,
        "enrollment_state": device.enrollment_state,
        "legacy_enrollment_eligible": device.legacy_enrollment_eligible,
        "registered_at": isoformat_utc(device.registered_at),
        "last_sync_at": isoformat_utc(device.last_sync_at),
        "active_policy_assignment": _assignment_summary(assignment)
        if assignment
        else None,
        "asset_number": device.asset_number,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "serial_number": _mask_serial(device.serial_number),
        "date_received": device.date_received.isoformat()
        if device.date_received
        else None,
        "condition": device.condition,
        "department": device.department,
        "asset_lifecycle_status": device.asset_lifecycle_status,
        "asset_notes": device.asset_notes,
        "enforcement_status": enforcement_status,
        "connection_status": connection_status,
        "connection_review": connection_review,
        "connection_review_after_days": connection_review_after_days,
        "last_compliance_check": isoformat_utc(state.last_received_at)
        if state
        else None,
        "failed_controls": failed_controls,
    }


def _device_detail(device: Device) -> dict[str, object]:
    summary = _device_summary(device)
    summary["created_at"] = isoformat_utc(device.created_at)
    summary["updated_at"] = isoformat_utc(device.updated_at)
    return summary


def _mask_serial(serial: str | None) -> str | None:
    if not serial:
        return serial
    if len(serial) <= 4:
        return "••••"
    return f"{'•' * max(4, len(serial) - 4)}{serial[-4:]}"


def _policy_summary(policy: Policy) -> dict[str, object]:
    latest_revision = db.session.scalars(
        select(PolicyRevision)
        .where(PolicyRevision.policy_id == policy.id)
        .order_by(PolicyRevision.version.desc())
        .limit(1)
    ).one_or_none()
    return {
        "policy_uuid": str(policy.policy_uuid),
        "name": policy.name,
        "status": policy.status,
        "created_at": isoformat_utc(policy.created_at),
        "updated_at": isoformat_utc(policy.updated_at),
        "latest_revision": _revision_summary(latest_revision)
        if latest_revision
        else None,
    }


def _policy_detail(policy: Policy) -> dict[str, object]:
    summary = _policy_summary(policy)
    summary["revision_count"] = int(
        db.session.scalar(
            select(func.count())
            .select_from(PolicyRevision)
            .where(PolicyRevision.policy_id == policy.id)
        )
        or 0
    )
    return summary


def _revision_summary(revision: PolicyRevision) -> dict[str, object]:
    return {
        "revision_uuid": str(revision.revision_uuid),
        "version": revision.version,
        "payload": revision.payload,
        "content_hash": revision.content_hash.hex(),
        "created_at": isoformat_utc(revision.created_at),
        "created_by": revision.created_by,
    }


def _assignment_summary(
    assignment: DevicePolicyAssignment,
) -> dict[str, object]:
    revision = assignment.policy_revision
    return {
        "event_uuid": str(assignment.event_uuid),
        "policy_revision_uuid": str(revision.revision_uuid),
        "policy_uuid": str(revision.policy.policy_uuid),
        "policy_name": revision.policy.name,
        "policy_version": revision.version,
        "status": assignment.status,
        "assigned_at": isoformat_utc(assignment.assigned_at),
        "superseded_at": isoformat_utc(assignment.superseded_at),
    }


def _enrollment_token_summary(token: EnrollmentToken) -> dict[str, object]:
    bound_device = (
        db.session.get(Device, token.bound_device_id)
        if token.bound_device_id is not None
        else None
    )
    consumed_device = (
        db.session.get(Device, token.consumed_by_device_id)
        if token.consumed_by_device_id is not None
        else None
    )
    administrator = db.session.scalars(
        select(Administrator).where(
            Administrator.administrator_uuid == UUID(token.issued_by)
        )
    ).one_or_none()
    policy_revision = token.policy_revision
    return {
        "token_uuid": str(token.token_uuid),
        "status": token.status,
        "bound_device_uuid": str(bound_device.device_uuid) if bound_device else None,
        "consumed_by_device_uuid": str(consumed_device.device_uuid)
        if consumed_device
        else None,
        "expires_at": isoformat_utc(token.expires_at),
        "created_at": isoformat_utc(token.created_at),
        "revoked_at": isoformat_utc(token.revoked_at),
        "issued_by": token.issued_by,
        "issued_by_name": administrator.display_name if administrator else None,
        "reason": token.reason,
        "policy_revision_uuid": str(policy_revision.revision_uuid)
        if policy_revision
        else None,
        "policy_name": policy_revision.policy.name if policy_revision else None,
        "policy_version": policy_revision.version if policy_revision else None,
    }


def _administrator_authentication_events(limit: int) -> list[dict[str, object]]:
    rows = db.session.scalars(
        select(AdministratorAuthenticationEvent)
        .order_by(
            AdministratorAuthenticationEvent.created_at.desc(),
            AdministratorAuthenticationEvent.id.desc(),
        )
        .limit(limit)
    ).all()
    return [
        {
            "event_type": "administrator_authentication",
            "event_uuid": str(row.event_uuid),
            "category": row.category,
            "occurred_at": isoformat_utc(row.created_at),
            "failure_class": row.failure_class,
        }
        for row in rows
        if row.category in ADMINISTRATOR_AUTHENTICATION_EVENT_CATEGORIES
    ]


def _device_enrollment_events(limit: int) -> list[dict[str, object]]:
    rows = db.session.scalars(
        select(DeviceEnrollmentEvent)
        .order_by(
            DeviceEnrollmentEvent.created_at.desc(), DeviceEnrollmentEvent.id.desc()
        )
        .limit(limit)
    ).all()
    return [
        {
            "event_type": "device_enrollment",
            "event_uuid": str(row.event_uuid),
            "category": row.category,
            "occurred_at": isoformat_utc(row.created_at),
            "failure_class": row.failure_class,
        }
        for row in rows
        if row.category in DEVICE_ENROLLMENT_EVENT_CATEGORIES
    ]


def _policy_assignment_events(limit: int) -> list[dict[str, object]]:
    rows = db.session.scalars(
        select(DevicePolicyAssignment)
        .options(
            joinedload(DevicePolicyAssignment.policy_revision).joinedload(
                PolicyRevision.policy
            )
        )
        .order_by(
            DevicePolicyAssignment.assigned_at.desc(), DevicePolicyAssignment.id.desc()
        )
        .limit(limit)
    ).all()
    return [
        {
            "event_type": "policy_assignment",
            "event_uuid": str(row.event_uuid),
            "category": row.status,
            "operation": "assign",
            "occurred_at": isoformat_utc(row.assigned_at),
            "device_uuid": str(row.device.device_uuid),
            "policy_revision_uuid": str(row.policy_revision.revision_uuid),
        }
        for row in rows
        if "assign" in POLICY_ASSIGNMENT_OPERATIONS
    ]


def _policy_change_summary(event: PolicyAssignmentEvent) -> dict[str, object]:
    assignment = (
        db.session.get(DevicePolicyAssignment, event.assignment_id)
        if event.assignment_id is not None
        else None
    )
    previous = (
        db.session.get(DevicePolicyAssignment, event.previous_assignment_id)
        if event.previous_assignment_id is not None
        else None
    )
    device = db.session.get(Device, event.device_id)
    administrator = db.session.get(Administrator, event.administrator_id)
    revision = (
        db.session.get(PolicyRevision, assignment.policy_revision_id)
        if assignment is not None
        else None
    )
    previous_revision = (
        db.session.get(PolicyRevision, previous.policy_revision_id)
        if previous is not None
        else None
    )
    sync = None
    if device is not None and revision is not None:
        sync = db.session.scalars(
            select(PolicySynchronizationEvent)
            .where(
                PolicySynchronizationEvent.device_id == device.id,
                PolicySynchronizationEvent.reported_revision_uuid
                == revision.revision_uuid,
            )
            .order_by(PolicySynchronizationEvent.requested_at.desc())
            .limit(1)
        ).first()
    if event.operation == "clear":
        result = "CLEARED"
    elif sync is not None and sync.outcome_category == "success":
        result = "APPLIED"
    else:
        result = "PENDING"
    return {
        "event_uuid": str(event.event_uuid),
        "policy_name": revision.policy.name if revision else None,
        "previous_policy_name": previous_revision.policy.name
        if previous_revision
        else None,
        "previous_version": previous_revision.version if previous_revision else None,
        "new_version": revision.version if revision else None,
        "administrator": administrator.display_name if administrator else None,
        "occurred_at": isoformat_utc(event.created_at),
        "device_uuid": str(device.device_uuid) if device else None,
        "asset_number": device.asset_number if device else None,
        "devices_affected": 1,
        "reason": event.reason,
        "operation": event.operation,
        "result": result,
    }


def _policy_synchronization_events(limit: int) -> list[dict[str, object]]:
    rows = db.session.scalars(
        select(PolicySynchronizationEvent)
        .order_by(
            PolicySynchronizationEvent.requested_at.desc(),
            PolicySynchronizationEvent.id.desc(),
        )
        .limit(limit)
    ).all()
    return [
        {
            "event_type": "policy_synchronization",
            "event_uuid": str(row.event_uuid),
            "category": row.outcome_category,
            "operation": row.operation,
            "occurred_at": isoformat_utc(row.requested_at),
        }
        for row in rows
        if row.operation in POLICY_SYNC_OPERATIONS
    ]


def _incident_events(limit: int) -> list[dict[str, object]]:
    rows = db.session.scalars(
        select(Incident)
        .options(joinedload(Incident.device))
        .order_by(Incident.reported_at.desc(), Incident.id.desc())
        .limit(limit)
    ).all()
    return [
        {
            "event_type": "incident",
            "event_uuid": str(row.incident_uuid),
            "category": row.status,
            "operation": row.incident_type,
            "occurred_at": isoformat_utc(row.reported_at),
            "device_uuid": str(row.device.device_uuid) if row.device else None,
        }
        for row in rows
    ]


def _device_asset_events(limit: int) -> list[dict[str, object]]:
    rows = db.session.scalars(
        select(DeviceAssetChangeEvent)
        .order_by(
            DeviceAssetChangeEvent.created_at.desc(), DeviceAssetChangeEvent.id.desc()
        )
        .limit(limit)
    ).all()
    return [
        {
            "event_type": "device_asset",
            "event_uuid": str(row.event_uuid),
            "category": row.operation,
            "operation": row.operation,
            "occurred_at": isoformat_utc(row.created_at),
            "device_uuid": str(row.device.device_uuid),
        }
        for row in rows
    ]


def _active_assignment(device_id: int) -> DevicePolicyAssignment | None:
    return db.session.scalars(
        select(DevicePolicyAssignment)
        .options(
            joinedload(DevicePolicyAssignment.policy_revision).joinedload(
                PolicyRevision.policy
            )
        )
        .where(
            DevicePolicyAssignment.device_id == device_id,
            DevicePolicyAssignment.status == "active",
        )
    ).one_or_none()


def _connection_review_threshold(
    assignment: DevicePolicyAssignment | None,
) -> int:
    if assignment is None:
        return 3
    payload = assignment.policy_revision.payload
    settings = payload.get("compliance_settings")
    if isinstance(settings, dict):
        threshold = settings.get("connection_review_after_days")
        if isinstance(threshold, int) and not isinstance(threshold, bool):
            return threshold
    return 3


def _uuid(value: object) -> UUID:
    return parse_canonical_uuid4(value)


AUDIT_EVENT_TYPES = frozenset(
    {
        "administrator_authentication",
        "device_enrollment",
        "policy_assignment",
        "policy_synchronization",
        "incident",
        "device_asset",
    }
)

__all__ = [
    "AUDIT_EVENT_TYPES",
    "AdminReadNotFoundError",
    "AdminReadPersistenceError",
    "PageResult",
    "list_audit_events",
    "list_policy_changes",
    "list_devices",
    "list_enrollment_tokens",
    "list_policies",
    "list_policy_revisions",
    "get_device",
    "get_device_policy_assignment",
    "get_policy",
]
