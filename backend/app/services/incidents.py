from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.admin_api import Pagination, isoformat_utc, pagination_payload
from app.extensions import db
from app.models import (
    INCIDENT_STATUSES,
    INCIDENT_TYPES,
    Administrator,
    Device,
    Incident,
    utc_now,
)


class IncidentValidationError(ValueError):
    pass


class IncidentNotFoundError(LookupError):
    pass


class IncidentConflictError(RuntimeError):
    pass


class IncidentPersistenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IncidentPage:
    items: list[dict[str, object]]
    pagination: dict[str, int | bool]


def list_incidents(
    pagination: Pagination,
    *,
    status: str | None = None,
    incident_type: str | None = None,
    device_uuid: UUID | None = None,
) -> IncidentPage:
    statement: Select[tuple[Incident]] = (
        select(Incident)
        .options(
            joinedload(Incident.device), joinedload(Incident.created_by_administrator)
        )
        .order_by(Incident.reported_at.desc(), Incident.id.desc())
    )
    count_statement = select(func.count()).select_from(Incident)
    if status is not None:
        statement = statement.where(Incident.status == status)
        count_statement = count_statement.where(Incident.status == status)
    if incident_type is not None:
        statement = statement.where(Incident.incident_type == incident_type)
        count_statement = count_statement.where(Incident.incident_type == incident_type)
    if device_uuid is not None:
        statement = statement.join(Device).where(Device.device_uuid == device_uuid)
        count_statement = count_statement.join(Device).where(
            Device.device_uuid == device_uuid
        )
    try:
        total = int(db.session.scalar(count_statement) or 0)
        rows = db.session.scalars(
            statement.offset(pagination.offset).limit(pagination.per_page)
        ).all()
        return IncidentPage(
            [_summary(row) for row in rows],
            pagination_payload(pagination, total=total),
        )
    except SQLAlchemyError as error:
        raise IncidentPersistenceError("incidents could not be loaded") from error


def create_incident(
    *,
    device_uuid: UUID | None,
    incident_type: object,
    description: object,
    reported_by: object,
    responsible_person: object | None,
    administrator: Administrator,
) -> dict[str, object]:
    checked_type = _choice(incident_type, INCIDENT_TYPES, "incident type")
    checked_description = _text(description, 2048, "description")
    checked_reported_by = _text(reported_by, 120, "reported by")
    checked_responsible = (
        _text(responsible_person, 120, "responsible person")
        if responsible_person is not None
        else None
    )
    try:
        device = None
        if device_uuid is not None:
            device = db.session.scalar(
                select(Device).where(Device.device_uuid == device_uuid)
            )
            if device is None:
                raise IncidentNotFoundError("device not found")
        now = utc_now()
        row = Incident(
            incident_uuid=UUID(int=0),
            incident_number="PENDING",
            device=device,
            incident_type=checked_type,
            description=checked_description,
            reported_by=checked_reported_by,
            reported_at=now,
            status="OPEN",
            responsible_person=checked_responsible,
            created_by_administrator_id=administrator.id,
            created_at=now,
            updated_at=now,
        )
        # The UUID is generated in Python while the number is generated from the
        # database id, giving administrators a short human-facing reference.
        from uuid import uuid4

        row.incident_uuid = uuid4()
        db.session.add(row)
        db.session.flush()
        row.incident_number = f"INC-{now:%Y%m%d}-{row.id:06d}"
        db.session.commit()
        return _summary(row)
    except (IncidentNotFoundError, IncidentValidationError):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise IncidentConflictError("incident could not be recorded") from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise IncidentPersistenceError("incident could not be recorded") from error


def update_incident(
    incident_uuid: UUID,
    *,
    status: object,
    action_taken: object | None,
    responsible_person: object | None,
    administrator: Administrator,
) -> dict[str, object]:
    checked_status = _choice(status, INCIDENT_STATUSES, "status")
    checked_action = (
        _text(action_taken, 2048, "action taken") if action_taken is not None else None
    )
    checked_responsible = (
        _text(responsible_person, 120, "responsible person")
        if responsible_person is not None
        else None
    )
    try:
        row = db.session.scalar(
            select(Incident)
            .where(Incident.incident_uuid == incident_uuid)
            .with_for_update()
        )
        if row is None:
            raise IncidentNotFoundError("incident not found")
        if row.status == "CLOSED":
            raise IncidentConflictError("closed incidents cannot be changed")
        if checked_status == "CLOSED" and not checked_action:
            raise IncidentValidationError("closed incidents require action taken")
        row.status = checked_status
        row.action_taken = checked_action
        row.responsible_person = checked_responsible
        row.updated_by_administrator_id = administrator.id
        row.updated_at = utc_now()
        row.closed_at = utc_now() if checked_status == "CLOSED" else None
        db.session.commit()
        return _summary(row)
    except (IncidentNotFoundError, IncidentConflictError, IncidentValidationError):
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        db.session.rollback()
        raise IncidentPersistenceError("incident could not be updated") from error


def _summary(row: Incident) -> dict[str, object]:
    return {
        "incident_uuid": str(row.incident_uuid),
        "incident_number": row.incident_number,
        "device_uuid": str(row.device.device_uuid) if row.device else None,
        "asset_number": row.device.asset_number if row.device else None,
        "incident_type": row.incident_type,
        "description": row.description,
        "reported_by": row.reported_by,
        "reported_at": isoformat_utc(row.reported_at),
        "status": row.status,
        "action_taken": row.action_taken,
        "responsible_person": row.responsible_person,
        "closed_at": isoformat_utc(row.closed_at),
        "created_by": row.created_by_administrator.display_name
        if row.created_by_administrator
        else None,
        "updated_at": isoformat_utc(row.updated_at),
    }


def _choice(value: object, choices: frozenset[str], field: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise IncidentValidationError(f"invalid {field}")
    return value


def _text(value: object, maximum: int, field: str) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= maximum
        or not value.isprintable()
    ):
        raise IncidentValidationError(f"invalid {field}")
    return value.strip()


__all__ = [
    "IncidentConflictError",
    "IncidentNotFoundError",
    "IncidentPage",
    "IncidentPersistenceError",
    "IncidentValidationError",
    "create_incident",
    "list_incidents",
    "update_incident",
]
