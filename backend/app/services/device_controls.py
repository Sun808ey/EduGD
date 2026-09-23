from __future__ import annotations

import hashlib
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import (
    Device,
    DeviceBlockOverride,
    DeviceControlEvent,
    DeviceUsageDaily,
    utc_now,
)
from app.policy_contract import canonical_json_bytes


class DeviceControlError(RuntimeError):
    pass


class DeviceControlNotFound(DeviceControlError):
    pass


class DeviceControlConflict(DeviceControlError):
    pass


def _reason(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= 512
        or not value.strip().isprintable()
    ):
        raise ValueError("invalid reason")
    return value.strip()


def set_block(
    device_uuid: UUID, administrator_id: int, reason: object
) -> DeviceBlockOverride:
    reason = _reason(reason)
    try:
        device = db.session.scalar(
            select(Device).where(Device.device_uuid == device_uuid).with_for_update()
        )
        if device is None:
            raise DeviceControlNotFound()
        override = db.session.scalar(
            select(DeviceBlockOverride)
            .where(DeviceBlockOverride.device_id == device.id)
            .with_for_update()
        )
        if override is None:
            override = DeviceBlockOverride(
                device_id=device.id,
                version=1,
                status="active",
                reason=reason,
                issued_by_administrator_id=administrator_id,
            )
            db.session.add(override)
            db.session.flush()
        elif override.status == "active":
            raise DeviceControlConflict("block is already active")
        else:
            override.version += 1
            override.status = "active"
            override.reason = reason
            override.issued_by_administrator_id = administrator_id
            override.issued_at = utc_now()
            override.cleared_by_administrator_id = None
            override.cleared_at = None
        _event(device.id, override.id, administrator_id, "block", reason)
        db.session.commit()
        return override
    except (DeviceControlError, ValueError):
        db.session.rollback()
        raise
    except (IntegrityError, SQLAlchemyError) as error:
        db.session.rollback()
        raise DeviceControlError("control state unavailable") from error


def clear_block(
    device_uuid: UUID, administrator_id: int, reason: object
) -> DeviceBlockOverride:
    reason = _reason(reason)
    try:
        device = db.session.scalar(
            select(Device).where(Device.device_uuid == device_uuid).with_for_update()
        )
        if device is None:
            raise DeviceControlNotFound()
        override = db.session.scalar(
            select(DeviceBlockOverride)
            .where(DeviceBlockOverride.device_id == device.id)
            .with_for_update()
        )
        if override is None or override.status != "active":
            raise DeviceControlConflict("no active block")
        override.status = "cleared"
        override.cleared_by_administrator_id = administrator_id
        override.cleared_at = utc_now()
        _event(device.id, override.id, administrator_id, "clear", reason)
        db.session.commit()
        return override
    except (DeviceControlError, ValueError):
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        db.session.rollback()
        raise DeviceControlError("control state unavailable") from error


def report_usage(device: Device, payload: object) -> DeviceUsageDaily:
    if not isinstance(payload, dict) or set(payload) != {
        "usage_date",
        "active_minutes",
        "policy_uuid",
        "revision_uuid",
    }:
        raise ValueError("invalid usage report")
    try:
        usage_date = date.fromisoformat(str(payload["usage_date"]))
        minutes = payload["active_minutes"]
        policy = UUID(str(payload["policy_uuid"]))
        revision = UUID(str(payload["revision_uuid"]))
        if (
            isinstance(minutes, bool)
            or not isinstance(minutes, int)
            or not 0 <= minutes <= 1440
        ):
            raise ValueError("invalid active_minutes")
    except (TypeError, ValueError) as error:
        raise ValueError("invalid usage report") from error
    try:
        row = db.session.scalar(
            select(DeviceUsageDaily)
            .where(
                DeviceUsageDaily.device_id == device.id,
                DeviceUsageDaily.usage_date == usage_date,
            )
            .with_for_update()
        )
        if row is None:
            row = DeviceUsageDaily(
                device_id=device.id,
                usage_date=usage_date,
                active_minutes=minutes,
                policy_uuid=policy,
                revision_uuid=revision,
            )
            db.session.add(row)
        elif (
            row.active_minutes > minutes
            or row.policy_uuid != policy
            or row.revision_uuid != revision
        ):
            raise DeviceControlConflict("usage report conflicts with stored state")
        else:
            row.active_minutes = minutes
            row.reported_at = utc_now()
        db.session.commit()
        return row
    except DeviceControlConflict:
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        db.session.rollback()
        raise DeviceControlError("usage storage unavailable") from error


def _event(
    device_id: int, override_id: int, administrator_id: int, operation: str, reason: str
) -> None:
    evidence = {
        "device_id": device_id,
        "override_id": override_id,
        "administrator_id": administrator_id,
        "operation": operation,
        "reason": reason,
        "at": utc_now().isoformat(),
    }
    db.session.add(
        DeviceControlEvent(
            device_id=device_id,
            override_id=override_id,
            administrator_id=administrator_id,
            operation=operation,
            reason=reason,
            content_hash=hashlib.sha256(canonical_json_bytes(evidence)).digest(),
        )
    )
