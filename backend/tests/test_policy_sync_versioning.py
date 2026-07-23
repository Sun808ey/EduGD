from uuid import UUID

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import (
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyRevision,
    policy_revision_content_hash,
)

DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"
POLICY_UUID = "8e65f112-f7c4-4776-b113-e0eef34ec881"
SYNC_URL = f"/api/v1/sync/policies/{DEVICE_UUID}"
BLOCKED_APPS = [
    "com.facebook.katana",
    "com.instagram.android",
]


def create_device_with_policy(*, assign_policy: bool = True) -> None:
    device = Device(
        device_uuid=UUID(DEVICE_UUID),
        android_version="10",
        api_level=29,
        status="active",
    )
    db.session.add(device)
    db.session.flush()

    if assign_policy:
        policy = Policy(
            policy_uuid=UUID(POLICY_UUID),
            name="Classroom policy",
            status="active",
        )
        db.session.add(policy)
        db.session.flush()
        payload = {"schema_version": 1, "blocked_apps": BLOCKED_APPS}
        revision = PolicyRevision(
            policy_id=policy.id,
            version=5,
            payload=payload,
            content_hash=policy_revision_content_hash(payload),
            created_by=POLICY_UUID,
        )
        db.session.add(revision)
        db.session.flush()
        db.session.add(
            DevicePolicyAssignment(
                device_id=device.id,
                policy_revision_id=revision.id,
                status="active",
            )
        )

    db.session.commit()


def test_version_aware_sync_returns_newer_policy(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        create_device_with_policy()

    response = client.get(f"{SYNC_URL}?current_version=4")

    assert response.status_code == 200
    assert response.get_json() == {
        "update_available": True,
        "policy": {
            "policy_uuid": POLICY_UUID,
            "policy_version": 5,
            "blocked_apps": BLOCKED_APPS,
        },
    }


@pytest.mark.parametrize("current_version", [5, 6])
def test_version_aware_sync_returns_no_update(
    client: FlaskClient,
    app: Flask,
    current_version: int,
) -> None:
    with app.app_context():
        create_device_with_policy()

    response = client.get(f"{SYNC_URL}?current_version={current_version}")

    assert response.status_code == 200
    assert response.get_json() == {
        "update_available": False,
        "policy_version": 5,
        "policy": None,
    }


def test_version_aware_sync_without_policy_returns_version_zero(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        create_device_with_policy(assign_policy=False)

    response = client.get(f"{SYNC_URL}?current_version=0")

    assert response.status_code == 200
    assert response.get_json() == {
        "update_available": False,
        "policy_version": 0,
        "policy": None,
    }


@pytest.mark.parametrize(
    "query_string",
    [
        "current_version=",
        "current_version=-1",
        "current_version=1.5",
        "current_version=+1",
        "current_version=%201",
        "current_version=abc",
        "current_version=%D9%A1",
        "current_version=1&current_version=2",
    ],
)
def test_version_aware_sync_rejects_invalid_version(
    client: FlaskClient,
    query_string: str,
) -> None:
    response = client.get(f"{SYNC_URL}?{query_string}")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "current_version must be a non-negative integer"
    }
