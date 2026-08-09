from uuid import UUID

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_migrate import upgrade
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

import app.routes.sync as sync_routes
from app import create_app
from app.extensions import db
from app.models import (
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyRevision,
    PolicySynchronizationEvent,
    PolicySynchronizationEventImmutableError,
    policy_revision_content_hash,
)

DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"
POLICY_UUID = "8e65f112-f7c4-4776-b113-e0eef34ec881"
SYNC_URL = f"/api/v1/sync/policies/{DEVICE_UUID}"
BLOCKED_APPS = ["com.facebook.katana", "com.instagram.android"]


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


def assign_active_policy(device: Device, *, policy_status: str = "active") -> str:
    policy = Policy(
        policy_uuid=UUID(POLICY_UUID),
        name="Classroom policy",
        status=policy_status,
    )
    db.session.add(policy)
    db.session.flush()
    payload = {"schema_version": 1, "blocked_apps": BLOCKED_APPS}
    revision = PolicyRevision(
        policy_id=policy.id,
        version=5,
        payload=payload,
        content_hash=policy_revision_content_hash(payload),
        created_by="migration:sync-route-test",
    )
    db.session.add(revision)
    db.session.flush()
    db.session.add(
        DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=revision.id,
            status="active",
            trusted_operator_subject="test:sync-route-fixture",
            reason="policy synchronization route fixture",
        )
    )
    db.session.commit()
    return str(revision.revision_uuid)


def test_legacy_sync_contract_is_preserved_and_deprecated(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        device = create_device()
        assign_active_policy(device)
    response = client.get(SYNC_URL)

    assert response.status_code == 200
    assert response.get_json() == {
        "device_uuid": DEVICE_UUID,
        "policy": {
            "policy_uuid": POLICY_UUID,
            "policy_version": 5,
            "blocked_apps": BLOCKED_APPS,
        },
    }
    assert response.headers["Deprecation"] == "true"
    assert "Sunset" in response.headers
    assert response.headers["Cache-Control"] == "no-store"


def test_legacy_no_policy_contract_is_preserved(
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


@pytest.mark.parametrize("policy_status", ["draft", "inactive", "revoked"])
def test_route_does_not_misclassify_unavailable_policy_as_no_assignment(
    client: FlaskClient,
    app: Flask,
    policy_status: str,
) -> None:
    with app.app_context():
        device = create_device()
        assign_active_policy(device, policy_status=policy_status)
    response = client.get(f"{SYNC_URL}?current_version=5")
    assert response.status_code == 409
    assert response.get_json()["operation"] == "blocked"
    assert response.get_json()["error"]["code"] == "policy_unavailable"

    with app.app_context():
        event = db.session.execute(select(PolicySynchronizationEvent)).scalar_one()
        assert event.outcome_category == (
            "policy_revoked" if policy_status == "revoked" else "policy_inactive"
        )


def test_unknown_device_uses_generic_non_enumerating_response(
    client: FlaskClient,
) -> None:
    response = client.get(SYNC_URL)
    assert response.status_code == 404
    assert response.get_json()["error"] == {
        "code": "sync_unavailable",
        "message": "policy synchronization unavailable",
    }
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("status", ["suspended", "retired"])
def test_inactive_device_is_explicitly_blocked(
    client: FlaskClient,
    app: Flask,
    status: str,
) -> None:
    with app.app_context():
        create_device(status=status)
    response = client.get(f"{SYNC_URL}?current_version=5")
    assert response.status_code == 403
    assert response.get_json()["operation"] == "blocked"
    assert response.get_json()["error"]["code"] == "device_blocked"


@pytest.mark.parametrize(
    "device_uuid",
    [
        "not-a-uuid",
        DEVICE_UUID.upper(),
        "{550e8400-e29b-41d4-a716-446655440000}",
        "550e8400e29b41d4a716446655440000",
        "00000000-0000-0000-0000-000000000000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    ],
)
def test_route_rejects_noncanonical_or_non_v4_uuid(
    client: FlaskClient,
    device_uuid: str,
) -> None:
    response = client.get(f"/api/v1/sync/policies/{device_uuid}")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_device_uuid"


def test_successful_sync_appends_hash_linked_audit_events(
    client: FlaskClient,
    app: Flask,
) -> None:
    with app.app_context():
        device = create_device()
        assign_active_policy(device)
        device_id = device.id
    assert client.get(f"{SYNC_URL}?current_version=4").status_code == 200
    assert client.get(f"{SYNC_URL}?current_version=5").status_code == 200

    with app.app_context():
        events = db.session.scalars(
            select(PolicySynchronizationEvent).order_by(PolicySynchronizationEvent.id)
        ).all()
        assert len(events) == 2
        assert events[0].previous_event_hash is None
        assert events[1].previous_event_hash == events[0].event_hash
        assert events[0].device_id == device_id
        assert events[0].event_uuid.version == 4
        assert events[0].reported_client_version == 4
        assert events[0].operation == "apply"
        assert events[1].operation == "no_change"
        stored_device = db.session.get(Device, device_id)
        assert stored_device is not None
        assert stored_device.last_sync_at is None

        events[0].operation = "error"
        with pytest.raises(PolicySynchronizationEventImmutableError):
            db.session.commit()
        db.session.rollback()


def test_route_hides_unexpected_database_error(
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
    assert response.get_json()["error"]["code"] == "internal_error"
    assert "forced database failure" not in response.get_data(as_text=True)


def test_sync_route_enforces_per_client_rate_limit() -> None:
    limited_app = create_app(
        "testing",
        {
            "RATELIMIT_ENABLED": True,
            "RATELIMIT_STORAGE_URI": "memory://",
            "POLICY_SYNC_RATE_LIMIT": "3 per minute",
        },
    )
    with limited_app.app_context():
        upgrade()
        create_device()
    client = limited_app.test_client()
    responses = [
        client.get(SYNC_URL, environ_base={"REMOTE_ADDR": "192.0.2.70"})
        for _ in range(4)
    ]
    assert all(response.status_code == 200 for response in responses[:3])
    assert responses[3].status_code == 429
    assert responses[3].get_json()["error"]["code"] == "rate_limit_exceeded"
    assert responses[3].headers["Cache-Control"] == "no-store"
