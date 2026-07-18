import json
from typing import Any
from uuid import UUID

import pytest
from flask import Flask
from sqlalchemy import event

from app.extensions import db
from app.models import Device, DevicePolicyAssignment, Policy, utc_now
from app.services.policy_sync import (
    DeviceBlockedError,
    DeviceNotFoundError,
    InvalidDeviceUUIDError,
    get_policy_sync_payload,
)

DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"
POLICY_UUID = "8e65f112-f7c4-4776-b113-e0eef34ec881"
BLOCKED_APPS = [
    "com.facebook.katana",
    "com.instagram.android",
]


def create_device(*, status: str = "active") -> Device:
    device = Device(
        device_uuid=UUID(DEVICE_UUID),
        android_version="10",
        status=status,
    )
    db.session.add(device)
    db.session.commit()
    return device


def assign_policy(
    device: Device,
    *,
    policy_status: str = "active",
    policy_version: int = 5,
    assignment_version: int = 5,
    assignment_status: str = "active",
) -> tuple[Policy, DevicePolicyAssignment]:
    policy = Policy(
        policy_uuid=UUID(POLICY_UUID),
        name="Classroom policy",
        version=policy_version,
        status=policy_status,
        blocked_apps=BLOCKED_APPS,
    )
    db.session.add(policy)
    db.session.flush()

    assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_id=policy.id,
        policy_version=assignment_version,
        status=assignment_status,
        superseded_at=(utc_now() if assignment_status == "superseded" else None),
    )
    db.session.add(assignment)
    db.session.commit()
    return policy, assignment


@pytest.mark.parametrize("device_uuid", [None, 10, "", "not-a-uuid"])
def test_policy_sync_rejects_invalid_device_uuid(
    app: Flask,
    device_uuid: Any,
) -> None:
    with app.app_context():
        with pytest.raises(InvalidDeviceUUIDError, match="invalid device UUID"):
            get_policy_sync_payload(device_uuid)


def test_policy_sync_rejects_unknown_device(app: Flask) -> None:
    with app.app_context():
        with pytest.raises(DeviceNotFoundError, match="device not found"):
            get_policy_sync_payload(DEVICE_UUID)


@pytest.mark.parametrize("status", ["suspended", "retired"])
def test_policy_sync_blocks_inactive_device_without_changing_policy(
    app: Flask,
    status: str,
) -> None:
    with app.app_context():
        device = create_device(status=status)
        _policy, assignment = assign_policy(device)

        with pytest.raises(DeviceBlockedError, match="device is not active"):
            get_policy_sync_payload(DEVICE_UUID)

        db.session.expire_all()
        stored_device = db.session.get(Device, device.id)
        stored_assignment = db.session.get(DevicePolicyAssignment, assignment.id)

    assert stored_device is not None
    assert stored_device.status == status
    assert stored_assignment is not None
    assert stored_assignment.status == "active"


def test_policy_sync_returns_no_policy_payload(app: Flask) -> None:
    with app.app_context():
        create_device()

        payload = get_policy_sync_payload(DEVICE_UUID.upper())

    assert payload == {
        "device_uuid": DEVICE_UUID,
        "policy": None,
        "policy_version": 0,
        "message": "no policy assigned",
    }


def test_policy_sync_returns_active_policy(app: Flask) -> None:
    with app.app_context():
        device = create_device()
        assign_policy(device)

        first_payload = get_policy_sync_payload(DEVICE_UUID.upper())
        second_payload = get_policy_sync_payload(DEVICE_UUID)

    expected_payload = {
        "device_uuid": DEVICE_UUID,
        "policy": {
            "policy_uuid": POLICY_UUID,
            "policy_version": 5,
            "blocked_apps": BLOCKED_APPS,
        },
    }
    assert first_payload == expected_payload
    assert second_payload == expected_payload
    assert json.loads(json.dumps(first_payload, sort_keys=True)) == first_payload


@pytest.mark.parametrize(
    "assignment_options",
    [
        {"assignment_status": "superseded"},
        {"policy_status": "inactive"},
        {"policy_version": 6, "assignment_version": 5},
    ],
)
def test_policy_sync_ignores_ineligible_policy(
    app: Flask,
    assignment_options: dict[str, Any],
) -> None:
    with app.app_context():
        device = create_device()
        assign_policy(device, **assignment_options)

        payload = get_policy_sync_payload(DEVICE_UUID)

    assert payload["policy"] is None
    assert payload["policy_version"] == 0


def test_policy_sync_is_database_read_only(app: Flask) -> None:
    with app.app_context():
        device = create_device()
        assign_policy(device)
        executed_operations: list[str] = []

        def record_operation(
            _connection: Any,
            _cursor: Any,
            statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            executed_operations.append(statement.lstrip().split(maxsplit=1)[0].upper())

        event.listen(db.engine, "before_cursor_execute", record_operation)
        try:
            get_policy_sync_payload(DEVICE_UUID)
        finally:
            event.remove(db.engine, "before_cursor_execute", record_operation)

        db.session.expire_all()
        stored_device = db.session.get(Device, device.id)

    assert executed_operations
    assert set(executed_operations) == {"SELECT"}
    assert stored_device is not None
    assert stored_device.last_sync_at is None
