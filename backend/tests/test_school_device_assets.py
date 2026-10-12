from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.models import Device
from app.services.administrator_authentication import bootstrap_administrator
from app.services.device_asset_privacy import (
    DeviceAssetNotFound,
    DeviceAssetPrivacyError,
    DeviceAssetRetentionError,
    correct_device_asset,
    correct_location_assignment,
    redact_retired_device,
)

USERNAME = "asset.admin"
PASSWORD = "AssetRegistration!2026"


def _headers(app: Flask) -> dict[str, str]:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="Asset Administrator",
            password=PASSWORD,
            operator_subject="test:asset-registration",
            reason="asset registration test bootstrap",
        )
    response = app.test_client().post(
        "/api/v1/admin/auth/login", json={"username": USERNAME, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.get_json()['access_token']}"}


def _payload() -> dict[str, object]:
    return {
        "asset_number": "EDUGD-TAB-001",
        "manufacturer": "Samsung",
        "model": "Galaxy Tab A",
        "serial_number": "SERIAL-001",
        "android_version": "13",
        "api_level": 33,
        "date_received": "2026-09-20",
        "condition": "Good",
        "department": "ICT Laboratory",
        "asset_lifecycle_status": "REGISTERED",
        "asset_notes": "Charger included",
    }


def test_school_owned_asset_registration_and_listing(app: Flask) -> None:
    client = app.test_client()
    headers = _headers(app)

    created = client.post(
        "/api/v1/admin/devices/assets", headers=headers, json=_payload()
    )
    assert created.status_code == 201
    device_uuid = created.get_json()["device_uuid"]

    devices = client.get("/api/v1/admin/devices", headers=headers).get_json()["devices"]
    asset = next(device for device in devices if device["device_uuid"] == device_uuid)
    assert asset["asset_number"] == "EDUGD-TAB-001"
    assert asset["serial_number"].endswith("-001")
    assert "SERIAL" not in asset["serial_number"]
    assert asset["date_received"] == "2026-09-20"
    assert asset["asset_lifecycle_status"] == "REGISTERED"
    assert asset["asset_notes"] == "Charger included"

    duplicate = client.post(
        "/api/v1/admin/devices/assets", headers=headers, json=_payload()
    )
    assert duplicate.status_code == 409


def test_school_owned_asset_registration_rejects_unauthorised_and_invalid_requests(
    app: Flask,
) -> None:
    client = app.test_client()
    assert (
        client.post("/api/v1/admin/devices/assets", json=_payload()).status_code == 401
    )

    invalid = _payload()
    invalid["asset_lifecycle_status"] = "NOT_A_STATE"
    assert (
        client.post(
            "/api/v1/admin/devices/assets", headers=_headers(app), json=invalid
        ).status_code
        == 400
    )


def test_asset_correction_is_minimised_and_audited(app: Flask) -> None:
    client = app.test_client()
    headers = _headers(app)
    created = client.post(
        "/api/v1/admin/devices/assets", headers=headers, json=_payload()
    )
    device_uuid = created.get_json()["device_uuid"]
    correction = {
        key: _payload()[key]
        for key in (
            "asset_number",
            "manufacturer",
            "model",
            "serial_number",
            "date_received",
            "condition",
            "department",
            "asset_lifecycle_status",
            "asset_notes",
        )
    }
    correction.update(
        {
            "asset_number": "EDUGD-TAB-001-CORRECTED",
            "reason": "Verified against the school inventory register",
        }
    )
    response = client.patch(
        f"/api/v1/admin/devices/{device_uuid}/asset", headers=headers, json=correction
    )
    assert response.status_code == 200
    events = client.get(
        "/api/v1/admin/audit-events?event_type=device_asset", headers=headers
    )
    assert events.status_code == 200
    event = events.get_json()["audit_events"][0]
    assert event["category"] == "corrected"
    assert "asset_number" not in event


def test_retired_asset_can_be_redacted_after_retention_window(app: Flask) -> None:
    client = app.test_client()
    headers = _headers(app)
    created = client.post(
        "/api/v1/admin/devices/assets", headers=headers, json=_payload()
    )
    device_uuid = created.get_json()["device_uuid"]
    retired = {
        key: _payload()[key]
        for key in (
            "asset_number",
            "manufacturer",
            "model",
            "serial_number",
            "date_received",
            "condition",
            "department",
            "asset_lifecycle_status",
            "asset_notes",
        )
    }
    retired.update({"asset_lifecycle_status": "RETIRED", "reason": "Asset retired"})
    retired_response = client.patch(
        f"/api/v1/admin/devices/{device_uuid}/asset", headers=headers, json=retired
    )
    assert retired_response.status_code == 200
    app.config["DEVICE_RETENTION_DAYS"] = 0
    with app.app_context():
        device = db.session.scalar(
            select(Device).where(Device.device_uuid == UUID(device_uuid))
        )
        assert device is not None
        device.updated_at = datetime.now(UTC) - timedelta(days=2)
        db.session.commit()
    response = client.post(
        f"/api/v1/admin/devices/{device_uuid}/data-retention/purge",
        headers=headers,
        json={"reason": "Approved retired-asset retention purge"},
    )
    assert response.status_code == 200
    with app.app_context():
        device = db.session.scalar(
            select(Device).where(Device.device_uuid == UUID(device_uuid))
        )
        assert device is not None
        assert device.status == "retired"
        assert device.serial_number is None
        assert device.asset_notes is None


def test_assignment_correction_requires_reason_and_is_audited(app: Flask) -> None:
    client = app.test_client()
    headers = _headers(app)
    created = client.post(
        "/api/v1/admin/devices/assets", headers=headers, json=_payload()
    )
    device_uuid = created.get_json()["device_uuid"]
    assignment = client.post(
        f"/api/v1/admin/devices/{device_uuid}/location-assignments",
        headers=headers,
        json={
            "target_type": "class",
            "target_name": "Senior One",
            "responsible_officer": "ICT Officer",
            "assigned_at": "2026-09-20",
            "expected_return_date": None,
            "issue_condition": "Good",
        },
    )
    assert assignment.status_code == 201
    assignment_uuid = assignment.get_json()["assignment"]["assignment_uuid"]
    correction = {
        "target_type": "class",
        "target_name": "Senior Two",
        "responsible_officer": "ICT Officer",
        "assigned_at": "2026-09-20",
        "expected_return_date": None,
        "issue_condition": "Good",
        "return_condition": None,
        "reason": "Corrected against timetable",
    }
    response = client.patch(
        f"/api/v1/admin/devices/{device_uuid}/location-assignments/{assignment_uuid}",
        headers=headers,
        json=correction,
    )
    assert response.status_code == 200
    assert response.get_json()["assignment"]["target_name"] == "Senior Two"


def test_asset_privacy_service_rejects_invalid_and_unsafe_mutations(app: Flask) -> None:
    with app.app_context():
        device = Device(device_uuid=uuid4(), android_version="13", api_level=33)
        db.session.add(device)
        db.session.commit()
        with pytest.raises(DeviceAssetPrivacyError):
            correct_device_asset("not-a-uuid", {}, administrator_id=1)
        with pytest.raises(DeviceAssetPrivacyError):
            correct_device_asset(str(device.device_uuid), {}, administrator_id=1)
        correction = {
            key: _payload()[key]
            for key in (
                "asset_number",
                "manufacturer",
                "model",
                "serial_number",
                "date_received",
                "condition",
                "department",
                "asset_lifecycle_status",
                "asset_notes",
            )
        }
        correction["reason"] = "verified correction"
        with pytest.raises(DeviceAssetNotFound):
            correct_device_asset(str(uuid4()), correction, administrator_id=1)
        with pytest.raises(DeviceAssetPrivacyError):
            redact_retired_device("not-a-uuid", administrator_id=1, reason="purge")
        with pytest.raises(DeviceAssetNotFound):
            redact_retired_device(str(uuid4()), administrator_id=1, reason="purge")
        with pytest.raises(DeviceAssetRetentionError):
            redact_retired_device(
                str(device.device_uuid), administrator_id=1, reason="purge"
            )
        with pytest.raises(DeviceAssetPrivacyError):
            correct_location_assignment(
                "not-a-uuid", str(uuid4()), {}, administrator_id=1
            )
        with pytest.raises(DeviceAssetNotFound):
            correct_location_assignment(
                str(uuid4()), str(uuid4()), {}, administrator_id=1
            )
