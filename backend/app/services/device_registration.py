from dataclasses import dataclass
from typing import Never
from uuid import UUID

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Device
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
            return _result_for_existing_device(
                existing_device,
                registration_data,
            )

        device = Device(
            device_uuid=registration_data.device_uuid,
            android_version=registration_data.android_version,
            api_level=registration_data.api_level,
            status="active",
        )
        db.session.add(device)
        response_data = _serialize_device(device)
        db.session.commit()
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

    return _result_for_existing_device(existing_device, registration_data)


def _result_for_existing_device(
    existing_device: Device,
    registration_data: DeviceRegistrationData,
) -> DeviceRegistrationResult:
    if (
        existing_device.android_version != registration_data.android_version
        or existing_device.api_level != registration_data.api_level
    ):
        raise DeviceRegistrationConflictError(
            "device UUID already registered with different data"
        )

    return DeviceRegistrationResult(
        device=_serialize_device(existing_device),
        created=False,
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
