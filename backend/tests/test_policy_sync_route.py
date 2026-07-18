from uuid import UUID

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import SQLAlchemyError

import app.routes.sync as sync_routes
from app.extensions import db
from app.models import Device, DevicePolicyAssignment, Policy

DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"
POLICY_UUID = "8e65f112-f7c4-4776-b113-e0eef34ec881"
SYNC_URL = f"/api/v1/sync/policies/{DEVICE_UUID}"
BLOCKED_APPS = [
    "com.facebook.katana",
    "com.instagram.android",
]


def create_device(*, status: str = "active") -> Device:
    device = Device(
        device_uuid=UUID(DEVICE_UUID),
        android_version="10",
        api_level=29,
        status=status,
    )
    db.session.add(device)
    db.session.commit()
    return device


def assign_active_policy(device: Device) -> None:
    policy = Policy(
        policy_uuid=UUID(POLICY_UUID),
        name="Classroom policy",
        version=5,
        status="active",
        blocked_apps=BLOCKED_APPS,
    )
    db.session.add(policy)
    db.session.flush()
    db.session.add(
        DevicePolicyAssignment(
            device_id=device.id,
            policy_id=policy.id,
            policy_version=policy.version,
            status="active",
        )
    )
    db.session.commit()


def test_policy_sync_route_returns_active_policy(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        device = create_device()
        assign_active_policy(device)

    response = client.get(SYNC_URL)

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "device_uuid": DEVICE_UUID,
        "policy": {
            "policy_uuid": POLICY_UUID,
            "policy_version": 5,
            "blocked_apps": BLOCKED_APPS,
        },
    }


def test_policy_sync_route_returns_no_policy(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        create_device()

    response = client.get(SYNC_URL)

    assert response.status_code == 200
    assert response.get_json() == {
        "device_uuid": DEVICE_UUID,
        "policy": None,
        "policy_version": 0,
        "message": "no policy assigned",
    }


def test_policy_sync_route_rejects_unknown_device(client: FlaskClient) -> None:
    response = client.get(SYNC_URL)

    assert response.status_code == 404
    assert response.get_json() == {"error": "device not found"}


@pytest.mark.parametrize("status", ["suspended", "retired"])
@pytest.mark.parametrize("query", ["", "?current_version=5"])
def test_policy_sync_route_blocks_inactive_device(
    client: FlaskClient,
    app: Flask,
    status: str,
    query: str,
) -> None:
    with app.app_context():
        device = create_device(status=status)
        assign_active_policy(device)

    response = client.get(f"{SYNC_URL}{query}")

    assert response.status_code == 403
    assert response.get_json() == {
        "error": "device is not active",
        "operation": "blocked",
    }


def test_policy_sync_route_rejects_invalid_uuid(client: FlaskClient) -> None:
    response = client.get("/api/v1/sync/policies/not-a-uuid")

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid device UUID"}


@pytest.mark.parametrize(
    "device_uuid",
    [
        DEVICE_UUID.upper(),
        "{550e8400-e29b-41d4-a716-446655440000}",
        "550e8400e29b41d4a716446655440000",
        "00000000-0000-0000-0000-000000000000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    ],
)
def test_policy_sync_route_rejects_noncanonical_or_non_v4_uuid(
    client: FlaskClient,
    device_uuid: str,
) -> None:
    response = client.get(f"/api/v1/sync/policies/{device_uuid}")

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid device UUID"}


def test_policy_sync_route_hides_unexpected_database_error(
    client: FlaskClient,
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_sync(_device_uuid: object) -> dict[str, object]:
        raise SQLAlchemyError("forced database failure")

    monkeypatch.setattr(sync_routes, "get_policy_sync_payload", fail_sync)
    app.logger.disabled = True

    response = client.get(SYNC_URL)

    assert response.status_code == 500
    assert response.get_json() == {"error": "internal server error"}
