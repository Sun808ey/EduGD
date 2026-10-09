from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.elements import ColumnElement

from app.admin_api import Pagination, isoformat_utc, pagination_payload
from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    Device,
    DeviceLocationAssignment,
    DeviceSecurityEvent,
    Policy,
    PolicyRevision,
)

VIOLATION_EVENT_CODES = frozenset(
    {
        "policy_block",
        "web_filter_blocked",
        "enforcement_failure",
        "tamper_attempt",
        "configuration_changed",
        "screen_time_exhausted",
    }
)


class ViolationReportPersistenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ViolationReportFilters:
    device_uuid: UUID | None = None
    class_name: str | None = None
    from_date: date | None = None
    to_date: date | None = None


def parse_report_date(value: str | None, field: str) -> date | None:
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def build_filters(
    *,
    device_uuid: str | None,
    class_name: str | None,
    from_date: str | None,
    to_date: str | None,
) -> ViolationReportFilters:
    parsed_device = parse_canonical_uuid4(device_uuid) if device_uuid else None
    normalized_class = class_name.strip() if class_name else None
    if normalized_class is not None and not 1 <= len(normalized_class) <= 120:
        raise ValueError("class_name must contain 1 to 120 characters")
    parsed_from = parse_report_date(from_date, "from")
    parsed_to = parse_report_date(to_date, "to")
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise ValueError("from must not be after to")
    return ViolationReportFilters(
        device_uuid=parsed_device,
        class_name=normalized_class,
        from_date=parsed_from,
        to_date=parsed_to,
    )


def list_violations(
    pagination: Pagination,
    filters: ViolationReportFilters,
) -> tuple[list[dict[str, object]], dict[str, int | bool]]:
    statement, count_statement = _statements(filters)
    try:
        total = int(db.session.scalar(count_statement) or 0)
        rows = db.session.execute(
            statement.order_by(
                DeviceSecurityEvent.occurred_at.desc(),
                DeviceSecurityEvent.sequence.desc(),
            )
            .offset(pagination.offset)
            .limit(pagination.per_page)
        ).all()
        return (
            [_violation_summary(event, device) for event, device in rows],
            pagination_payload(pagination, total=total),
        )
    except SQLAlchemyError as error:
        raise ViolationReportPersistenceError(
            "violation report could not be loaded"
        ) from error


def all_violations(filters: ViolationReportFilters) -> list[dict[str, object]]:
    statement, _ = _statements(filters)
    try:
        rows = db.session.execute(
            statement.order_by(
                DeviceSecurityEvent.occurred_at.desc(),
                DeviceSecurityEvent.sequence.desc(),
            )
        ).all()
        return [_violation_summary(event, device) for event, device in rows]
    except SQLAlchemyError as error:
        raise ViolationReportPersistenceError(
            "violation report could not be loaded"
        ) from error


def _statements(
    filters: ViolationReportFilters,
) -> tuple[Select[tuple[DeviceSecurityEvent, Device]], Select[tuple[int]]]:
    conditions: list[ColumnElement[bool]] = [
        DeviceSecurityEvent.event_code.in_(VIOLATION_EVENT_CODES)
    ]
    if filters.device_uuid is not None:
        conditions.append(Device.device_uuid == filters.device_uuid)
    if filters.class_name is not None:
        conditions.append(
            db.session.query(DeviceLocationAssignment.device_id)
            .filter(
                DeviceLocationAssignment.device_id == Device.id,
                DeviceLocationAssignment.target_type == "class",
                DeviceLocationAssignment.target_name == filters.class_name,
            )
            .exists()
        )
    if filters.from_date is not None:
        start = datetime.combine(filters.from_date, time.min, tzinfo=UTC)
        conditions.append(DeviceSecurityEvent.occurred_at >= start)
    if filters.to_date is not None:
        end = datetime.combine(
            filters.to_date + timedelta(days=1), time.min, tzinfo=UTC
        )
        conditions.append(DeviceSecurityEvent.occurred_at < end)
    statement = (
        select(DeviceSecurityEvent, Device)
        .join(Device, Device.id == DeviceSecurityEvent.device_id)
        .where(*conditions)
    )
    count_statement = (
        select(func.count())
        .select_from(DeviceSecurityEvent)
        .join(Device, Device.id == DeviceSecurityEvent.device_id)
        .where(*conditions)
    )
    return statement, count_statement


def _violation_summary(
    event: DeviceSecurityEvent,
    device: Device,
) -> dict[str, object]:
    policy = (
        db.session.scalar(select(Policy).where(Policy.policy_uuid == event.policy_uuid))
        if event.policy_uuid
        else None
    )
    revision = (
        db.session.scalar(
            select(PolicyRevision).where(
                PolicyRevision.revision_uuid == event.revision_uuid
            )
        )
        if event.revision_uuid
        else None
    )
    class_assignment = db.session.scalars(
        select(DeviceLocationAssignment)
        .where(
            DeviceLocationAssignment.device_id == device.id,
            DeviceLocationAssignment.target_type == "class",
        )
        .order_by(DeviceLocationAssignment.assigned_at.desc())
        .limit(1)
    ).first()
    metadata = event.event_metadata if isinstance(event.event_metadata, dict) else {}
    details = {
        key: metadata[key]
        for key in ("package_name", "setting", "message", "domain_hash", "attempt")
        if key in metadata
    }
    return {
        "event_uuid": str(event.event_uuid),
        "device_uuid": str(device.device_uuid),
        "asset_number": device.asset_number,
        "class_name": class_assignment.target_name if class_assignment else None,
        "event_code": event.event_code,
        "violation_type": _violation_type(event.event_code),
        "outcome": event.outcome,
        "rule_id": event.rule_id,
        "details": details,
        "policy_uuid": str(event.policy_uuid) if event.policy_uuid else None,
        "policy_name": policy.name if policy else None,
        "policy_version": revision.version if revision else None,
        "occurred_at": isoformat_utc(event.occurred_at),
        "received_at": isoformat_utc(event.received_at),
        "sequence": event.sequence,
        "event_hash": event.event_hash.hex(),
        "previous_event_hash": event.previous_event_hash.hex()
        if event.previous_event_hash
        else None,
    }


def _violation_type(event_code: str) -> str:
    return {
        "policy_block": "Blocked application or device action",
        "web_filter_blocked": "Blocked web domain",
        "enforcement_failure": "Policy enforcement failure",
        "tamper_attempt": "Tamper or bypass attempt",
        "configuration_changed": "Restricted configuration change",
        "screen_time_exhausted": "Screen-time limit reached",
    }.get(event_code, event_code.replace("_", " ").title())


__all__ = [
    "ViolationReportFilters",
    "ViolationReportPersistenceError",
    "all_violations",
    "build_filters",
    "list_violations",
]
