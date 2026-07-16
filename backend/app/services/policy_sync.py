from uuid import UUID

from sqlalchemy import select

from app.extensions import db
from app.models import Device, DevicePolicyAssignment, Policy


class InvalidDeviceUUIDError(ValueError):
    def __init__(self) -> None:
        super().__init__("invalid device UUID")


class DeviceNotFoundError(LookupError):
    def __init__(self) -> None:
        super().__init__("device not found")


def get_policy_sync_payload(device_uuid: object) -> dict[str, object]:
    canonical_uuid = _canonicalize_device_uuid(device_uuid)

    with db.session.no_autoflush:
        device = _find_device(canonical_uuid)
        if device is None:
            raise DeviceNotFoundError()

        assignment = _find_active_assignment(device.id)
        if assignment is None:
            return _no_policy_payload(canonical_uuid)

        policy = _find_matching_active_policy(assignment)
        if policy is None:
            return _no_policy_payload(canonical_uuid)

        return {
            "device_uuid": str(canonical_uuid),
            "policy": {
                "policy_uuid": str(policy.policy_uuid),
                "policy_version": assignment.policy_version,
                "blocked_apps": list(policy.blocked_apps),
            },
        }


def _canonicalize_device_uuid(device_uuid: object) -> UUID:
    if not isinstance(device_uuid, str) or not device_uuid:
        raise InvalidDeviceUUIDError()

    try:
        return UUID(device_uuid)
    except (AttributeError, ValueError) as error:
        raise InvalidDeviceUUIDError() from error


def _find_device(device_uuid: UUID) -> Device | None:
    statement = select(Device).where(Device.device_uuid == device_uuid)
    return db.session.execute(statement).scalar_one_or_none()


def _find_active_assignment(device_id: int) -> DevicePolicyAssignment | None:
    statement = (
        select(DevicePolicyAssignment)
        .where(
            DevicePolicyAssignment.device_id == device_id,
            DevicePolicyAssignment.status == "active",
        )
        .order_by(
            DevicePolicyAssignment.assigned_at.desc(),
            DevicePolicyAssignment.id.desc(),
        )
        .limit(1)
    )
    return db.session.execute(statement).scalar_one_or_none()


def _find_matching_active_policy(
    assignment: DevicePolicyAssignment,
) -> Policy | None:
    statement = select(Policy).where(
        Policy.id == assignment.policy_id,
        Policy.status == "active",
        Policy.version == assignment.policy_version,
    )
    return db.session.execute(statement).scalar_one_or_none()


def _no_policy_payload(device_uuid: UUID) -> dict[str, object]:
    return {
        "device_uuid": str(device_uuid),
        "policy": None,
        "policy_version": 0,
        "message": "no policy assigned",
    }


__all__ = [
    "DeviceNotFoundError",
    "InvalidDeviceUUIDError",
    "get_policy_sync_payload",
]
