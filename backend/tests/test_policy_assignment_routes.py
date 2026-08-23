from uuid import uuid4

from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.models import (
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyAssignmentChainHead,
    PolicyAssignmentEvent,
    PolicyRevision,
    policy_revision_content_hash,
)
from app.services.administrator_authentication import bootstrap_administrator
from app.services.audit_verification import verify_policy_assignment_chain

USERNAME = "policy.admin"
PASSWORD = "OfflineSchool!2026"


def _setup(app: Flask) -> tuple[str, str, dict[str, str]]:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="Policy Administrator",
            password=PASSWORD,
            operator_subject="test:policy-routes",
            reason="policy route test bootstrap",
        )
        device = Device(device_uuid=uuid4(), android_version="10", api_level=29)
        policy = Policy(policy_uuid=uuid4(), name="Route policy")
        payload = {"schema_version": 1, "blocked_apps": ["org.example.blocked"]}
        revision = PolicyRevision(
            policy=policy,
            version=1,
            payload=payload,
            content_hash=policy_revision_content_hash(payload),
            created_by="migration:policy-route-test",
        )
        db.session.add_all([device, policy, revision])
        db.session.commit()
        device_uuid = str(device.device_uuid)
        revision_uuid = str(revision.revision_uuid)
    login = app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    token = login.get_json()["access_token"]
    return device_uuid, revision_uuid, {"Authorization": f"Bearer {token}"}


def test_assign_and_clear_create_linear_immutable_evidence(app: Flask) -> None:
    device_uuid, revision_uuid, headers = _setup(app)
    client = app.test_client()
    assignment = client.post(
        f"/api/v1/admin/devices/{device_uuid}/policy-assignment",
        json={"policy_revision_uuid": revision_uuid, "reason": "Approved policy"},
        headers=headers,
    )
    clearing = client.post(
        f"/api/v1/admin/devices/{device_uuid}/policy-assignment/clear",
        json={"reason": "Approved end of policy period"},
        headers=headers,
    )
    repeated_clear = client.post(
        f"/api/v1/admin/devices/{device_uuid}/policy-assignment/clear",
        json={"reason": "Duplicate clear"},
        headers=headers,
    )

    assert assignment.status_code == 200
    assert assignment.headers["Cache-Control"] == "no-store"
    assert clearing.status_code == 200
    assert clearing.get_json()["clear_intent"]["operation"] == "clear"
    assert repeated_clear.status_code == 409
    with app.app_context():
        events = db.session.scalars(
            select(PolicyAssignmentEvent).order_by(PolicyAssignmentEvent.id)
        ).all()
        assert [event.operation for event in events] == ["assign", "clear"]
        assert events[1].previous_event_hash == events[0].event_hash
        head = db.session.execute(select(PolicyAssignmentChainHead)).scalar_one()
        assert head.head_event_hash == events[1].event_hash
        stored_assignment = db.session.execute(
            select(DevicePolicyAssignment)
        ).scalar_one()
        assert stored_assignment.status == "superseded"
        verify_policy_assignment_chain(stored_assignment.device_id)


def test_policy_mutation_contract_rejects_auth_and_invalid_json(app: Flask) -> None:
    device_uuid, _revision_uuid, headers = _setup(app)
    url = f"/api/v1/admin/devices/{device_uuid}/policy-assignment"
    missing_auth = app.test_client().post(url, json={})
    invalid = app.test_client().post(
        url,
        json={"policy_revision_uuid": "not-a-uuid", "reason": "Invalid"},
        headers=headers,
    )
    unknown_field = app.test_client().post(
        url,
        json={
            "policy_revision_uuid": str(uuid4()),
            "reason": "Invalid",
            "unexpected": True,
        },
        headers=headers,
    )

    assert missing_auth.status_code == 401
    assert missing_auth.get_json()["error"]["code"] == "authentication_failed"
    assert invalid.status_code == 400
    assert unknown_field.status_code == 400


def test_policy_mutation_contract_rejects_media_type_reason_and_missing_device(
    app: Flask,
) -> None:
    device_uuid, revision_uuid, headers = _setup(app)
    client = app.test_client()
    url = f"/api/v1/admin/devices/{device_uuid}/policy-assignment"
    wrong_media = client.post(url, data="{}", headers=headers)
    invalid_reason = client.post(
        url,
        json={"policy_revision_uuid": revision_uuid, "reason": "line\nbreak"},
        headers=headers,
    )
    missing_device = client.post(
        f"/api/v1/admin/devices/{uuid4()}/policy-assignment",
        json={"policy_revision_uuid": revision_uuid, "reason": "Approved"},
        headers=headers,
    )

    assert wrong_media.status_code == 415
    assert wrong_media.get_json()["error"]["code"] == "unsupported_media_type"
    assert invalid_reason.status_code == 400
    assert missing_device.status_code == 404
