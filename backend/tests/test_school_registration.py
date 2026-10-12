from __future__ import annotations

from flask import Flask

from app.services.administrator_authentication import bootstrap_administrator
from app.services.school_registration import SchoolRegistrationUnavailable

USERNAME = "school.admin"
PASSWORD = "SchoolRegistration!2026"


def _headers(app: Flask) -> dict[str, str]:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="School Administrator",
            password=PASSWORD,
            operator_subject="test:school-registration",
            reason="school registration test bootstrap",
        )
    response = app.test_client().post(
        "/api/v1/admin/auth/login", json={"username": USERNAME, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.get_json()['access_token']}"}


def _payload() -> dict[str, object]:
    return {
        "name": "Example Secondary School",
        "district": "Kampala",
        "school_type": "Secondary",
        "contact_person": "ICT Officer",
        "official_telephone": "+256 700 000 000",
        "official_email": "ict@example.edu.ug",
        "physical_location": "Kampala",
        "authorised_administrator_name": "School Administrator",
    }


def test_school_registration_is_singleton_and_minimises_data(app: Flask) -> None:
    headers = _headers(app)
    client = app.test_client()

    assert client.get("/api/v1/admin/school", headers=headers).get_json() == {
        "school": None
    }

    created = client.post("/api/v1/admin/school", headers=headers, json=_payload())
    assert created.status_code == 201
    school = created.get_json()["school"]
    assert school["name"] == "Example Secondary School"
    assert "learner" not in school

    assert (
        client.get("/api/v1/admin/school", headers=headers).get_json()["school"][
            "school_uuid"
        ]
        == school["school_uuid"]
    )
    assert (
        client.post(
            "/api/v1/admin/school", headers=headers, json=_payload()
        ).status_code
        == 409
    )


def test_school_registration_rejects_invalid_or_unauthorised_requests(
    app: Flask,
) -> None:
    client = app.test_client()
    assert client.post("/api/v1/admin/school", json=_payload()).status_code == 401

    headers = _headers(app)
    invalid = _payload()
    invalid["official_telephone"] = "invalid"
    assert (
        client.post("/api/v1/admin/school", headers=headers, json=invalid).status_code
        == 400
    )


def test_school_profile_can_be_edited_and_rejects_invalid_updates(app: Flask) -> None:
    headers = _headers(app)
    client = app.test_client()
    created = client.post("/api/v1/admin/school", headers=headers, json=_payload())
    assert created.status_code == 201
    updated_payload = {
        **_payload(),
        "name": "Updated Example Secondary School",
        "timezone": "UTC",
    }
    updated = client.patch(
        "/api/v1/admin/school", headers=headers, json=updated_payload
    )
    assert updated.status_code == 200
    assert updated.get_json()["school"]["name"] == "Updated Example Secondary School"
    assert updated.get_json()["school"]["timezone"] == "UTC"
    assert (
        client.patch(
            "/api/v1/admin/school", headers=headers, json={"name": "incomplete"}
        ).status_code
        == 400
    )


def test_school_profile_maps_unavailable_update(app: Flask, monkeypatch) -> None:
    headers = _headers(app)
    client = app.test_client()
    client.post("/api/v1/admin/school", headers=headers, json=_payload())
    monkeypatch.setattr(
        "app.routes.schools.update_school",
        lambda **_: (_ for _ in ()).throw(SchoolRegistrationUnavailable()),
    )
    assert (
        client.patch(
            "/api/v1/admin/school",
            headers=headers,
            json={**_payload(), "timezone": "UTC"},
        ).status_code
        == 503
    )
