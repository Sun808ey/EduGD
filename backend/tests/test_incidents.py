from uuid import uuid4

from flask import Flask

from app.extensions import db
from app.models import Device
from app.services.administrator_authentication import bootstrap_administrator

USERNAME = "incident.admin"
PASSWORD = "OfflineSchool!2026"


def _setup(app: Flask) -> tuple[str, dict[str, str]]:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="Incident Administrator",
            password=PASSWORD,
            operator_subject="test:incidents",
            reason="incident test bootstrap",
        )
        device = Device(device_uuid=uuid4(), android_version="10", api_level=29)
        db.session.add(device)
        db.session.commit()
        device_uuid = str(device.device_uuid)
    login = app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    return device_uuid, {"Authorization": f"Bearer {login.get_json()['access_token']}"}


def test_manual_incident_entry_is_disabled(app: Flask) -> None:
    device_uuid, headers = _setup(app)
    client = app.test_client()
    response = client.post(
        "/api/v1/admin/incidents",
        json={
            "device_uuid": device_uuid,
            "incident_type": "device_missing",
            "description": "Tablet was not returned after the ICT session.",
            "reported_by": "ICT officer",
            "responsible_person": "ICT department",
        },
        headers=headers,
    )
    assert response.status_code == 410
    assert response.get_json()["error"]["code"] == "manual_incidents_disabled"

    device_incidents = client.get(
        f"/api/v1/admin/devices/{device_uuid}/incidents", headers=headers
    )
    assert device_incidents.status_code == 200
    assert device_incidents.get_json()["incidents"] == []


def test_manual_incident_updates_are_disabled(app: Flask) -> None:
    _, headers = _setup(app)
    client = app.test_client()
    response = client.patch(
        f"/api/v1/admin/incidents/{uuid4()}",
        json={"status": "CLOSED", "action_taken": None, "responsible_person": None},
        headers=headers,
    )
    assert response.status_code == 410
    assert response.get_json()["error"]["code"] == "manual_incidents_disabled"
