import json
from typing import Any, cast
from uuid import uuid4

from flask import Flask
from sqlalchemy import func, select

from app.extensions import db
from app.models import (
    Administrator,
    Device,
    DeviceCheckIn,
    DeviceComplianceState,
    DevicePolicyState,
    Policy,
    PolicyApplicationEvent,
    PolicyRevision,
    policy_revision_content_hash,
)
from tests.test_device_enrollment_authentication import (
    DEVICE_UUID,
    _bootstrap_and_login,
    _enrollment_payload,
    _issue_token,
    _key_material,
    _signed_headers,
)


def _enroll(app: Flask):
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    response = app.test_client().post(
        "/api/v1/devices/register",
        json=_enrollment_payload(token, private_key, public_key, fingerprint),
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.get_json())["credential_uuid"], private_key


def _post(
    app: Flask, private_key: Any, credential_uuid: str, suffix: str, payload: object
):
    path = f"/api/v1/devices/{DEVICE_UUID}/{suffix}"
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers, _ = _signed_headers(
        private_key, credential_uuid, method="POST", path=path, body=body
    )
    return app.test_client().post(
        path, data=body, content_type="application/json", headers=headers
    )


def _check_in(observed_at: str = "2026-09-20T12:00:00Z") -> dict[str, object]:
    return {
        "protocol_version": 3,
        "check_in_uuid": str(uuid4()),
        "observed_at": observed_at,
        "elapsed_realtime_ms": 1000,
        "boot_count": 1,
        "dpc_version": 1,
        "android_version": "10",
        "api_level": 29,
        "security_patch": "2026-09-01",
        "capabilities": ["package_suspension", "lock_task"],
        "current_policy_uuid": None,
        "current_revision_uuid": None,
        "policy_status": "none",
        "enforcement_healthy": True,
        "queued_event_count": 2,
    }


def test_check_in_updates_compliance_projection_and_is_idempotent(app: Flask) -> None:
    credential_uuid, private_key = _enroll(app)
    payload = _check_in()
    response = _post(app, private_key, credential_uuid, "check-ins", payload)
    assert response.status_code == 200
    assert response.get_json()["replayed"] is False

    replay = _post(app, private_key, credential_uuid, "check-ins", payload)
    assert replay.status_code == 200
    assert replay.get_json()["replayed"] is True

    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(DeviceCheckIn)) == 1
        state = db.session.execute(select(DeviceComplianceState)).scalar_one()
        device = db.session.execute(select(Device)).scalar_one()
        assert state.policy_status == "none"
        assert state.capabilities == ["lock_task", "package_suspension"]
        assert state.queued_event_count == 2
        assert device.last_sync_at is not None


def test_older_check_in_is_preserved_without_regressing_projection(app: Flask) -> None:
    credential_uuid, private_key = _enroll(app)
    current = _check_in("2026-09-20T12:00:00Z")
    older = _check_in("2026-09-20T11:00:00Z")
    older["queued_event_count"] = 99
    assert (
        _post(app, private_key, credential_uuid, "check-ins", current).status_code
        == 200
    )
    assert (
        _post(app, private_key, credential_uuid, "check-ins", older).status_code == 200
    )
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(DeviceCheckIn)) == 2
        assert (
            db.session.execute(select(DeviceComplianceState))
            .scalar_one()
            .queued_event_count
            == 2
        )


def test_check_in_rejects_android_identity_drift(app: Flask) -> None:
    credential_uuid, private_key = _enroll(app)
    payload = _check_in()
    payload["api_level"] = 30
    response = _post(app, private_key, credential_uuid, "check-ins", payload)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "status_conflict"


def test_policy_acknowledgement_records_known_revision(app: Flask) -> None:
    credential_uuid, private_key = _enroll(app)
    with app.app_context():
        administrator = db.session.execute(select(Administrator)).scalar_one()
        policy = Policy(policy_uuid=uuid4(), name="Pilot policy", status="active")
        db.session.add(policy)
        db.session.flush()
        payload = {"schema_version": 1, "blocked_apps": ["com.example.game"]}
        revision = PolicyRevision(
            policy_id=policy.id,
            version=1,
            payload=payload,
            content_hash=policy_revision_content_hash(payload),
            created_by=str(administrator.administrator_uuid),
            created_by_administrator_id=administrator.id,
        )
        db.session.add(revision)
        db.session.commit()
        policy_uuid = str(policy.policy_uuid)
        revision_uuid = str(revision.revision_uuid)

    acknowledgement = {
        "protocol_version": 3,
        "acknowledgement_uuid": str(uuid4()),
        "observed_at": "2026-09-20T12:00:00Z",
        "elapsed_realtime_ms": 1000,
        "boot_count": 1,
        "policy_uuid": policy_uuid,
        "revision_uuid": revision_uuid,
        "outcome": "applied",
        "error_code": None,
    }
    response = _post(
        app, private_key, credential_uuid, "policy-acknowledgements", acknowledgement
    )
    assert response.status_code == 200
    with app.app_context():
        event = db.session.execute(select(PolicyApplicationEvent)).scalar_one()
        state = db.session.execute(select(DevicePolicyState)).scalar_one()
        assert event.outcome == "applied"
        assert state.revision_uuid == event.revision_uuid


def test_policy_acknowledgement_rejects_unknown_revision(app: Flask) -> None:
    credential_uuid, private_key = _enroll(app)
    acknowledgement = {
        "protocol_version": 3,
        "acknowledgement_uuid": str(uuid4()),
        "observed_at": "2026-09-20T12:00:00Z",
        "elapsed_realtime_ms": 1000,
        "boot_count": 1,
        "policy_uuid": str(uuid4()),
        "revision_uuid": str(uuid4()),
        "outcome": "applied",
        "error_code": None,
    }
    response = _post(
        app, private_key, credential_uuid, "policy-acknowledgements", acknowledgement
    )
    assert response.status_code == 409
