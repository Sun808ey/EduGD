"""Privacy controls for the school-owned asset register.

Corrections retain only the names of changed fields in the audit trail. A
retired asset can be redacted after the configured retention window; its
non-personal UUID remains as an integrity anchor for immutable device evidence.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Device, DeviceAssetChangeEvent, DeviceLocationAssignment

EDITABLE_ASSET_FIELDS = frozenset(
    {
        "asset_number",
        "manufacturer",
        "model",
        "serial_number",
        "date_received",
        "condition",
        "department",
        "asset_lifecycle_status",
        "asset_notes",
    }
)
RETENTION_REDACTABLE_FIELDS = (
    "asset_number",
    "manufacturer",
    "model",
    "serial_number",
    "date_received",
    "condition",
    "department",
    "asset_notes",
)


class DeviceAssetPrivacyError(RuntimeError):
    pass


class DeviceAssetNotFound(DeviceAssetPrivacyError):
    pass


class DeviceAssetConflict(DeviceAssetPrivacyError):
    pass


class DeviceAssetRetentionError(DeviceAssetPrivacyError):
    pass


def correct_device_asset(
    device_uuid: str,
    payload: dict[str, object],
    *,
    administrator_id: int,
) -> Device:
    try:
        parsed_uuid = UUID(device_uuid)
    except (ValueError, TypeError) as error:
        raise DeviceAssetPrivacyError("device_uuid must be a UUID") from error
    if set(payload) != EDITABLE_ASSET_FIELDS | {"reason"}:
        raise DeviceAssetPrivacyError("invalid asset correction request")
    reason = _text(payload["reason"], 512)
    try:
        device = db.session.scalar(
            select(Device).where(Device.device_uuid == parsed_uuid).with_for_update()
        )
        if device is None:
            raise DeviceAssetNotFound("device not found")
        if (
            device.status == "retired"
            and payload["asset_lifecycle_status"] != "RETIRED"
        ):
            raise DeviceAssetPrivacyError("retired devices cannot be reactivated")
        values = _validated_values(payload)
        changed = [
            field
            for field in EDITABLE_ASSET_FIELDS
            if getattr(device, field) != values[field]
        ]
        if not changed:
            raise DeviceAssetPrivacyError("correction does not change the asset")
        for field in changed:
            setattr(device, field, values[field])
        if values["asset_lifecycle_status"] == "RETIRED":
            device.status = "retired"
        db.session.add(
            DeviceAssetChangeEvent(
                device_id=device.id,
                administrator_id=administrator_id,
                operation="corrected",
                changed_fields=changed,
                reason=reason,
            )
        )
        db.session.commit()
        return device
    except (DeviceAssetPrivacyError, ValueError):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise DeviceAssetConflict(
            "asset number or serial number already exists"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise DeviceAssetPrivacyError("asset correction unavailable") from error


def redact_retired_device(
    device_uuid: str,
    *,
    administrator_id: int,
    reason: str,
) -> Device:
    try:
        parsed_uuid = UUID(device_uuid)
    except (ValueError, TypeError) as error:
        raise DeviceAssetPrivacyError("device_uuid must be a UUID") from error
    try:
        device = db.session.scalar(
            select(Device).where(Device.device_uuid == parsed_uuid).with_for_update()
        )
        if device is None:
            raise DeviceAssetNotFound("device not found")
        if device.status != "retired" or device.asset_lifecycle_status != "RETIRED":
            raise DeviceAssetRetentionError("only retired assets may be redacted")
        updated_at = device.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        retention_days = int(current_app.config["DEVICE_RETENTION_DAYS"])
        if datetime.now(UTC) < updated_at + timedelta(days=retention_days):
            raise DeviceAssetRetentionError("asset retention window has not elapsed")
        safe_reason = _text(reason, 512)
        changed = [
            field
            for field in RETENTION_REDACTABLE_FIELDS
            if getattr(device, field) is not None
        ]
        for field in RETENTION_REDACTABLE_FIELDS:
            setattr(device, field, None)
        db.session.query(DeviceLocationAssignment).filter(
            DeviceLocationAssignment.device_id == device.id
        ).delete(synchronize_session=False)
        db.session.add(
            DeviceAssetChangeEvent(
                device_id=device.id,
                administrator_id=administrator_id,
                operation="retention_redacted",
                changed_fields=changed or ["location_assignments"],
                reason=safe_reason,
            )
        )
        db.session.commit()
        return device
    except (DeviceAssetPrivacyError, ValueError):
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        db.session.rollback()
        raise DeviceAssetPrivacyError("retention redaction unavailable") from error


def correct_location_assignment(
    device_uuid: str,
    assignment_uuid: str,
    payload: dict[str, object],
    *,
    administrator_id: int,
) -> DeviceLocationAssignment:
    try:
        device_id = db.session.scalar(
            select(Device.id).where(Device.device_uuid == UUID(device_uuid))
        )
        if device_id is None:
            raise DeviceAssetNotFound("device not found")
        assignment = db.session.scalar(
            select(DeviceLocationAssignment)
            .where(
                DeviceLocationAssignment.assignment_uuid == UUID(assignment_uuid),
                DeviceLocationAssignment.device_id == device_id,
            )
            .with_for_update()
        )
    except (ValueError, TypeError) as error:
        raise DeviceAssetPrivacyError("assignment UUID is invalid") from error
    if assignment is None:
        raise DeviceAssetNotFound("assignment not found")
    if set(payload) != {
        "target_type",
        "target_name",
        "responsible_officer",
        "assigned_at",
        "expected_return_date",
        "issue_condition",
        "return_condition",
        "reason",
    }:
        raise DeviceAssetPrivacyError("invalid assignment correction request")
    assigned_at = _parse_date(payload["assigned_at"])
    expected_return_date = _parse_optional_date(payload["expected_return_date"])
    values = {
        "target_type": payload["target_type"],
        "target_name": _text(payload["target_name"], 120),
        "responsible_officer": _text(payload["responsible_officer"], 120),
        "issue_condition": _text(payload["issue_condition"], 80),
        "return_condition": None
        if payload["return_condition"] in (None, "")
        else _text(payload["return_condition"], 80),
        "assigned_at": assigned_at,
        "expected_return_date": expected_return_date,
    }
    if values["target_type"] not in {"class", "department"}:
        raise DeviceAssetPrivacyError("invalid assignment target type")
    if expected_return_date is not None and expected_return_date < assigned_at:
        raise DeviceAssetPrivacyError("expected return date precedes assignment")
    if values["return_condition"] is not None and assignment.returned_at is None:
        raise DeviceAssetPrivacyError("return condition requires a returned assignment")
    changed = [field for field in values if getattr(assignment, field) != values[field]]
    if not changed:
        raise DeviceAssetPrivacyError("correction does not change the assignment")
    try:
        for field in changed:
            setattr(assignment, field, values[field])
        db.session.add(
            DeviceAssetChangeEvent(
                device_id=device_id,
                administrator_id=administrator_id,
                operation="corrected",
                changed_fields=[f"assignment.{field}" for field in changed],
                reason=_text(payload["reason"], 512),
            )
        )
        db.session.commit()
        return assignment
    except (DeviceAssetPrivacyError, ValueError):
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        db.session.rollback()
        raise DeviceAssetPrivacyError("assignment correction unavailable") from error


def _validated_values(payload: dict[str, object]) -> dict[str, object]:
    values: dict[str, object] = {}
    limits = {
        "asset_number": 80,
        "manufacturer": 120,
        "model": 120,
        "serial_number": 160,
        "condition": 80,
        "department": 120,
        "asset_lifecycle_status": 32,
    }
    for field, maximum in limits.items():
        values[field] = _text(payload[field], maximum)
    if values["asset_lifecycle_status"] not in {
        "REGISTERED",
        "READY_FOR_PROVISIONING",
        "PROVISIONING",
        "ENROLLED",
        "COMPLIANT",
        "ASSIGNED",
        "RETURNED",
        "RETIRED",
        "PROVISIONING_FAILED",
        "NON_COMPLIANT",
        "MISSING",
        "DAMAGED",
    }:
        raise DeviceAssetPrivacyError("invalid lifecycle status")
    raw_date = payload["date_received"]
    try:
        values["date_received"] = date.fromisoformat(str(raw_date))
    except (TypeError, ValueError) as error:
        raise DeviceAssetPrivacyError("invalid date_received") from error
    notes = payload["asset_notes"]
    if notes is not None and (
        not isinstance(notes, str) or len(notes) > 512 or not notes.isprintable()
    ):
        raise DeviceAssetPrivacyError("invalid asset notes")
    values["asset_notes"] = (
        notes.strip() if isinstance(notes, str) and notes.strip() else None
    )
    return values


def _text(value: object, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= maximum
        or not value.isprintable()
    ):
        raise DeviceAssetPrivacyError("invalid asset text")
    return value.strip()


def _parse_date(value: object) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise DeviceAssetPrivacyError("invalid assignment date") from error


def _parse_optional_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    return _parse_date(value)
