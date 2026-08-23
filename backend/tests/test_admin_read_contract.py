from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.admin_api import isoformat_utc
from app.extensions import db
from app.models import (
    Administrator,
    Device,
    DeviceEnrollmentEvent,
    EnrollmentToken,
    Policy,
    PolicyRevision,
    policy_revision_content_hash,
    utc_now,
)
from app.services.administrator_authentication import bootstrap_administrator

USERNAME = "readiness.admin"
PASSWORD = "OfflineSchool!2026"


def _seed(app: Flask) -> tuple[str, str, dict[str, str]]:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="Readiness Administrator",
            password=PASSWORD,
            operator_subject="test:readiness",
            reason="readiness API test bootstrap",
        )
        administrator = db.session.scalars(
            select(Administrator).where(Administrator.username == USERNAME)
        ).one()
        active_device = Device(
            device_uuid=uuid4(),
            android_version="10",
            api_level=29,
            status="active",
        )
        suspended_device = Device(
            device_uuid=uuid4(),
            android_version="9",
            api_level=28,
            status="suspended",
        )
        policy = Policy(policy_uuid=uuid4(), name="Readiness policy", status="active")
        payload = {"schema_version": 1, "blocked_apps": ["org.example.blocked"]}
        revision = PolicyRevision(
            policy=policy,
            version=1,
            payload=payload,
            content_hash=policy_revision_content_hash(payload),
            created_by="migration:readiness-contract-test",
        )
        token = EnrollmentToken(
            verifier=b"v" * 32,
            pepper_version=1,
            status="active",
            expires_at=utc_now() + timedelta(minutes=10),
            issued_by=str(administrator.administrator_uuid),
            reason="contract readiness",
        )
        db.session.add_all([active_device, suspended_device, policy, revision, token])
        db.session.flush()
        db.session.add(
            DeviceEnrollmentEvent(
                device_id=active_device.id,
                category="token_issued",
                administrator_subject=str(administrator.administrator_uuid),
                reason="contract readiness",
            )
        )
        db.session.commit()
        device_uuid = str(active_device.device_uuid)
        policy_uuid = str(policy.policy_uuid)

    login = app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    access_token = login.get_json()["access_token"]
    return device_uuid, policy_uuid, {"Authorization": f"Bearer {access_token}"}


def test_admin_read_endpoints_return_contract_ready_payloads(app: Flask) -> None:
    device_uuid, policy_uuid, headers = _seed(app)
    client = app.test_client()

    devices = client.get("/api/v1/admin/devices?per_page=1", headers=headers)
    device = client.get(f"/api/v1/admin/devices/{device_uuid}", headers=headers)
    assignment = client.get(
        f"/api/v1/admin/devices/{device_uuid}/policy-assignment",
        headers=headers,
    )
    policies = client.get("/api/v1/admin/policies", headers=headers)
    policy = client.get(f"/api/v1/admin/policies/{policy_uuid}", headers=headers)
    revisions = client.get(
        f"/api/v1/admin/policies/{policy_uuid}/revisions",
        headers=headers,
    )
    tokens = client.get("/api/v1/admin/enrollment-tokens", headers=headers)
    audit = client.get("/api/v1/admin/audit-events", headers=headers)

    assert devices.status_code == 200
    assert devices.get_json()["pagination"] == {
        "page": 1,
        "per_page": 1,
        "total": 2,
        "has_next": True,
    }
    assert device.status_code == 200
    assert device.get_json()["device"]["device_uuid"] == device_uuid
    assert assignment.status_code == 200
    assert assignment.get_json()["policy_assignment"]["assignment"] is None
    assert policies.status_code == 200
    assert policies.get_json()["policies"][0]["latest_revision"]["version"] == 1
    assert policy.status_code == 200
    assert policy.get_json()["policy"]["revision_count"] == 1
    assert revisions.status_code == 200
    assert revisions.get_json()["revisions"][0]["payload"]["blocked_apps"] == [
        "org.example.blocked"
    ]
    assert tokens.status_code == 200
    assert tokens.get_json()["enrollment_tokens"][0]["status"] == "active"
    assert audit.status_code == 200
    assert audit.get_json()["audit_events"][0]["event_uuid"]
    assert all(
        response.headers["Cache-Control"] == "no-store"
        for response in (
            devices,
            device,
            assignment,
            policies,
            policy,
            revisions,
            tokens,
            audit,
        )
    )


def test_admin_read_endpoints_enforce_auth_and_standard_errors(app: Flask) -> None:
    device_uuid, _policy_uuid, _headers = _seed(app)
    client = app.test_client()

    missing_auth = client.get("/api/v1/admin/devices")
    invalid_page = client.get(
        "/api/v1/admin/devices?per_page=101",
        headers=_headers,
    )
    invalid_filter = client.get(
        "/api/v1/admin/policies?status=deleted",
        headers=_headers,
    )
    missing_device = client.get(
        f"/api/v1/admin/devices/{uuid4()}",
        headers=_headers,
    )
    invalid_uuid = client.get(
        "/api/v1/admin/devices/not-a-uuid",
        headers=_headers,
    )

    assert missing_auth.status_code == 401
    assert missing_auth.get_json()["error"]["code"] == "authentication_failed"
    assert invalid_page.status_code == 400
    assert invalid_page.get_json()["error"]["code"] == "invalid_pagination"
    assert invalid_filter.status_code == 400
    assert invalid_filter.get_json()["error"]["code"] == "invalid_filter"
    assert missing_device.status_code == 404
    assert missing_device.get_json()["error"]["code"] == "device_not_found"
    assert invalid_uuid.status_code == 400
    assert invalid_uuid.get_json()["error"]["code"] == "invalid_device_uuid"
    assert device_uuid not in missing_auth.get_data(as_text=True)


def test_admin_read_filters_and_not_found_contracts(app: Flask) -> None:
    _device_uuid, policy_uuid, headers = _seed(app)
    client = app.test_client()

    devices = client.get("/api/v1/admin/devices?status=suspended", headers=headers)
    policies = client.get("/api/v1/admin/policies?status=active", headers=headers)
    tokens = client.get(
        "/api/v1/admin/enrollment-tokens?status=active",
        headers=headers,
    )
    audit = client.get(
        "/api/v1/admin/audit-events?event_type=device_enrollment",
        headers=headers,
    )
    missing_policy = client.get(f"/api/v1/admin/policies/{uuid4()}", headers=headers)
    invalid_policy = client.get("/api/v1/admin/policies/not-a-uuid", headers=headers)
    missing_revisions = client.get(
        f"/api/v1/admin/policies/{uuid4()}/revisions",
        headers=headers,
    )
    revisions = client.get(
        f"/api/v1/admin/policies/{policy_uuid}/revisions?page=1&per_page=25",
        headers=headers,
    )
    invalid_audit = client.get(
        "/api/v1/admin/audit-events?event_type=secret",
        headers=headers,
    )
    invalid_page = client.get("/api/v1/admin/devices?page=abc", headers=headers)
    with app.app_context():
        empty_policy = Policy(policy_uuid=uuid4(), name="Empty policy", status="draft")
        db.session.add(empty_policy)
        db.session.commit()
    draft_policies = client.get("/api/v1/admin/policies?status=draft", headers=headers)

    assert devices.status_code == 200
    assert devices.get_json()["devices"][0]["status"] == "suspended"
    assert policies.status_code == 200
    assert policies.get_json()["policies"][0]["status"] == "active"
    assert tokens.status_code == 200
    assert tokens.get_json()["enrollment_tokens"][0]["status"] == "active"
    assert audit.status_code == 200
    assert audit.get_json()["audit_events"][0]["event_type"] == "device_enrollment"
    assert missing_policy.status_code == 404
    assert missing_policy.get_json()["error"]["code"] == "policy_not_found"
    assert invalid_policy.status_code == 400
    assert invalid_policy.get_json()["error"]["code"] == "invalid_policy_uuid"
    assert missing_revisions.status_code == 404
    assert missing_revisions.get_json()["error"]["code"] == "policy_not_found"
    assert revisions.status_code == 200
    assert revisions.get_json()["pagination"]["total"] == 1
    assert invalid_audit.status_code == 400
    assert invalid_audit.get_json()["error"]["code"] == "invalid_filter"
    assert invalid_page.status_code == 400
    assert invalid_page.get_json()["error"]["code"] == "invalid_pagination"
    assert draft_policies.status_code == 200
    assert draft_policies.get_json()["policies"][0]["latest_revision"] is None
    assert isoformat_utc(None) is None


def test_admin_read_persistence_errors_fail_closed(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _device_uuid, _policy_uuid, headers = _seed(app)

    def fail_scalar(*_args: object, **_kwargs: object) -> object:
        raise SQLAlchemyError("forced read failure")

    monkeypatch.setattr(db.session, "scalar", fail_scalar)

    response = app.test_client().get("/api/v1/admin/devices", headers=headers)

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "read_unavailable"


def test_admin_detail_persistence_errors_fail_closed(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device_uuid, policy_uuid, headers = _seed(app)

    def fail_scalars(*_args: object, **_kwargs: object) -> object:
        raise SQLAlchemyError("forced detail failure")

    monkeypatch.setattr(db.session, "scalars", fail_scalars)
    client = app.test_client()

    responses = [
        client.get(f"/api/v1/admin/devices/{device_uuid}", headers=headers),
        client.get(
            f"/api/v1/admin/devices/{device_uuid}/policy-assignment",
            headers=headers,
        ),
        client.get(f"/api/v1/admin/policies/{policy_uuid}", headers=headers),
        client.get(
            f"/api/v1/admin/policies/{policy_uuid}/revisions",
            headers=headers,
        ),
        client.get("/api/v1/admin/audit-events", headers=headers),
    ]

    assert all(response.status_code == 503 for response in responses)
    assert all(
        response.get_json()["error"]["code"] == "read_unavailable"
        for response in responses
    )
