from uuid import UUID, uuid4

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
BLOCKED_APPS = ["com.facebook.katana", "com.instagram.android"]


def create_device_with_policy(*, assign_policy: bool = True) -> str | None:
    device = Device(
        device_uuid=UUID(DEVICE_UUID),
        android_version="10",
        api_level=29,
        status="active",
    )
    db.session.add(device)
    db.session.flush()
    revision_uuid: str | None = None
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
            created_by="migration:sync-operation-test",
        )
        db.session.add(revision)
        db.session.flush()
        revision_uuid = str(revision.revision_uuid)
        db.session.add(
            DevicePolicyAssignment(
                device_id=device.id,
                policy_revision_id=revision.id,
                status="active",
                trusted_operator_subject="test:sync-version-fixture",
                reason="policy synchronization version fixture",
            )
        )
    db.session.commit()
    return revision_uuid


def _identity_query(version: int, policy_uuid: str, revision_uuid: str) -> str:
    return (
        f"current_version={version}&current_policy_uuid={policy_uuid}"
        f"&current_revision_uuid={revision_uuid}"
    )


def test_version_aware_sync_returns_apply_with_exact_revision_identity(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        revision_uuid = create_device_with_policy()
    response = client.get(f"{SYNC_URL}?current_version=4")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "device_uuid": DEVICE_UUID,
        "operation": "apply",
        "server_policy_version": 5,
        "policy": {
            "policy_uuid": POLICY_UUID,
            "policy_revision_uuid": revision_uuid,
            "policy_version": 5,
            "blocked_apps": BLOCKED_APPS,
        },
    }
    assert response.headers["Cache-Control"] == "no-store"


def test_version_aware_sync_returns_no_change_for_exact_revision(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        revision_uuid = create_device_with_policy()
    assert revision_uuid is not None
    response = client.get(
        f"{SYNC_URL}?{_identity_query(5, POLICY_UUID, revision_uuid)}"
    )
    assert response.status_code == 200
    assert response.get_json()["operation"] == "no_change"
    assert response.get_json()["policy"]["policy_revision_uuid"] == revision_uuid


def test_version_aware_sync_returns_rollback_only_for_same_policy(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        create_device_with_policy()
    response = client.get(f"{SYNC_URL}?{_identity_query(6, POLICY_UUID, str(uuid4()))}")
    assert response.status_code == 200
    assert response.get_json()["operation"] == "rollback"

    different_policy_response = client.get(
        f"{SYNC_URL}?{_identity_query(6, str(uuid4()), str(uuid4()))}"
    )
    assert different_policy_response.status_code == 200
    assert different_policy_response.get_json()["operation"] == "apply"


@pytest.mark.parametrize(
    ("version", "expected_operation"),
    [(0, "no_change"), (1, "clear")],
)
def test_version_aware_sync_explicitly_represents_policy_removal(
    client: FlaskClient,
    app: Flask,
    version: int,
    expected_operation: str,
) -> None:
    with app.app_context():
        create_device_with_policy(assign_policy=False)
    response = client.get(f"{SYNC_URL}?current_version={version}")
    assert response.status_code == 200
    assert response.get_json() == {
        "device_uuid": DEVICE_UUID,
        "operation": expected_operation,
        "server_policy_version": 0,
        "policy": None,
    }


@pytest.mark.parametrize(
    "query_string",
    [
        "current_version=",
        "current_version=-1",
        "current_version=+1",
        "current_version=1.5",
        "current_version=%D9%A1",
        "current_version=2147483648",
        "current_version=10000000000",
        f"current_version={'9' * 5000}",
        "current_version=1&current_version=2",
    ],
)
def test_version_aware_sync_rejects_invalid_or_oversized_version(
    client: FlaskClient,
    query_string: str,
) -> None:
    response = client.get(f"{SYNC_URL}?{query_string}")
    assert response.status_code == 400
    assert response.get_json()["error"] == {
        "code": "invalid_request",
        "message": "current_version must be an integer from 0 to 2147483647",
    }
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("version", [0, 2_147_483_647])
def test_version_aware_sync_accepts_approved_bounds(
    client: FlaskClient,
    app: Flask,
    version: int,
) -> None:
    with app.app_context():
        create_device_with_policy(assign_policy=False)
    response = client.get(f"{SYNC_URL}?current_version={version}")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "query",
    [
        f"current_version=1&current_policy_uuid={POLICY_UUID}",
        f"current_version=1&current_revision_uuid={uuid4()}",
        f"current_version=1&current_policy_uuid=invalid&current_revision_uuid={uuid4()}",
    ],
)
def test_version_aware_sync_rejects_partial_or_invalid_identity(
    client: FlaskClient,
    query: str,
) -> None:
    response = client.get(f"{SYNC_URL}?{query}")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"
