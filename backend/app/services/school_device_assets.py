from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Device

ASSET_STATES = frozenset(
    {
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
    }
)


class AssetRegistrationError(RuntimeError):
    pass


class AssetRegistrationConflict(AssetRegistrationError):
    pass


def register_asset(payload: dict[str, object]) -> Device:
    try:
        android_version = payload["android_version"]
        api_level = payload["api_level"]
        lifecycle = payload["asset_lifecycle_status"]
        if (
            not isinstance(android_version, str)
            or not isinstance(api_level, int)
            or isinstance(api_level, bool)
            or lifecycle not in ASSET_STATES
        ):
            raise ValueError("invalid asset")
        values = {
            key: str(payload[key]).strip()
            for key in (
                "asset_number",
                "manufacturer",
                "model",
                "serial_number",
                "condition",
                "department",
            )
        }
        if any(not value for value in values.values()):
            raise ValueError("invalid asset")
        notes = payload.get("asset_notes")
        if notes is not None and (not isinstance(notes, str) or len(notes) > 512):
            raise ValueError("invalid notes")
        device = Device(
            device_uuid=uuid4(),
            android_version=android_version,
            api_level=api_level,
            status="active" if 29 <= api_level <= 35 else "suspended",
            legacy_enrollment_eligible=False,
            date_received=date.fromisoformat(str(payload["date_received"])),
            asset_lifecycle_status=lifecycle,
            asset_notes=notes.strip()
            if isinstance(notes, str) and notes.strip()
            else None,
            **values,
        )
        db.session.add(device)
        db.session.commit()
        return device
    except (KeyError, TypeError, ValueError) as error:
        db.session.rollback()
        raise AssetRegistrationError("invalid device asset") from error
    except IntegrityError as error:
        db.session.rollback()
        raise AssetRegistrationConflict(
            "duplicate asset number or serial number"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise AssetRegistrationError("device asset unavailable") from error
