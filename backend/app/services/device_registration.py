from dataclasses import dataclass
from typing import Never
from uuid import UUID

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Device, DeviceRegistrationEvent
from app.schemas import DeviceRegistrationData


@dataclass(frozen=True, slots=True)
class RegisteredDeviceData:
    device_uuid: str
    android_version: str
    api_level: int
    status: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "device_uuid": self.device_uuid,
            "android_version": self.android_version,
            "api_level": self.api_level,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class DeviceRegistrationResult:
    device: RegisteredDeviceData
    created: bool


class DeviceRegistrationConflictError(ValueError):
    pass


class DeviceRegistrationDatabaseError(RuntimeError):
    pass


def register_device(
    registration_data: DeviceRegistrationData,
) -> DeviceRegistrationResult:
    try:
        existing_device = _find_device(registration_data.device_uuid)
        if existing_device is not None:
            return _complete_existing_registration(
                existing_device,
                registration_data,
            )

        device = Device(
            device_uuid=registration_data.device_uuid,
            android_version=registration_data.android_version,
            api_level=registration_data.api_level,
            status="active",
            legacy_enrollment_eligible=(
                current_app.config["DEVICE_ENROLLMENT_MODE"] == "legacy"
            ),
        )
        db.session.add(device)
        db.session.flush()
        _record_registration_event(device, registration_data, "registered")
        response_data = _serialize_device(device)
        db.session.commit()
        _log_registration_outcome("device_registration_created")
        return DeviceRegistrationResult(
            device=response_data,
            created=True,
        )
    except IntegrityError as error:
        db.session.rollback()
        return _resolve_concurrent_duplicate(registration_data, error)
    except SQLAlchemyError as error:
        _raise_database_error(error)


def _find_device(device_uuid: UUID) -> Device | None:
    statement = select(Device).where(Device.device_uuid == device_uuid)
    return db.session.execute(statement).scalar_one_or_none()


def _resolve_concurrent_duplicate(
    registration_data: DeviceRegistrationData,
    original_error: IntegrityError,
) -> DeviceRegistrationResult:
    try:
        existing_device = _find_device(registration_data.device_uuid)
    except SQLAlchemyError as error:
        _raise_database_error(error)

    if existing_device is None:
        current_app.logger.error(
            "Device registration failed with an unresolved integrity error",
            extra={"event": "device_registration_integrity_error"},
        )
        raise DeviceRegistrationDatabaseError(
            "device registration database operation failed"
        ) from original_error

    return _complete_existing_registration(existing_device, registration_data)


def _complete_existing_registration(
    existing_device: Device,
    registration_data: DeviceRegistrationData,
) -> DeviceRegistrationResult:
    if existing_device.api_level < registration_data.api_level:
        event_type = "upgrade_requires_authentication"
        conflict_message = (
            "device metadata upgrade requires authenticated synchronization"
        )
    elif existing_device.api_level > registration_data.api_level:
        event_type = "downgrade_rejected"
        conflict_message = "reported Android downgrade rejected"
    elif existing_device.android_version != registration_data.android_version:
        event_type = "downgrade_rejected"
        conflict_message = "reported Android metadata conflicts with stored data"
    else:
        event_type = "duplicate"
        conflict_message = None

    _record_registration_event(existing_device, registration_data, event_type)
    db.session.commit()
    _log_registration_outcome(f"device_registration_{event_type}")

    if conflict_message is not None:
        raise DeviceRegistrationConflictError(conflict_message)

    return DeviceRegistrationResult(
        device=_serialize_device(existing_device),
        created=False,
    )


def _record_registration_event(
    device: Device,
    registration_data: DeviceRegistrationData,
    event_type: str,
) -> None:
    db.session.add(
        DeviceRegistrationEvent(
            device_id=device.id,
            event_type=event_type,
            stored_android_version=device.android_version,
            stored_api_level=device.api_level,
            reported_android_version=registration_data.android_version,
            reported_api_level=registration_data.api_level,
        )
    )


def _log_registration_outcome(event_name: str) -> None:
    current_app.logger.info(
        "Device registration lifecycle event completed",
        extra={"event": event_name},
    )


def _serialize_device(device: Device) -> RegisteredDeviceData:
    return RegisteredDeviceData(
        device_uuid=str(device.device_uuid),
        android_version=device.android_version,
        api_level=device.api_level,
        status=device.status,
    )


def _raise_database_error(error: SQLAlchemyError) -> Never:
    db.session.rollback()
    current_app.logger.error(
        "Device registration database operation failed",
        exc_info=True,
        extra={"event": "device_registration_database_error"},
    )
    raise DeviceRegistrationDatabaseError(
        "device registration database operation failed"
    ) from error


__all__ = [
    "DeviceRegistrationConflictError",
    "DeviceRegistrationDatabaseError",
    "DeviceRegistrationResult",
    "RegisteredDeviceData",
    "register_device",
]
