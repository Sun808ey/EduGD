from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app.device_cryptography import decode_base64url, encode_base64url
from app.routes.managed_applications import _parse_domain_payload, _parse_payload
from tests.test_administrator_authentication import (
    _authorization_header,
    _bootstrap,
    _login,
)


def _payload(*, digest: str | None) -> dict[str, object]:
    return {
        "display_name": "Verified learning app",
        "package_name": "org.example.learning",
        "signing_certificate_sha256": digest,
        "category": "education",
        "education_approved": True,
        "mandatory_block": False,
        "status": "enabled",
    }


def test_managed_application_requires_verified_signing_digest(app: Flask) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    headers = _authorization_header(token)

    missing = app.test_client().post(
        "/api/v1/admin/applications",
        headers=headers,
        json=_payload(digest=None),
    )
    valid = app.test_client().post(
        "/api/v1/admin/applications",
        headers=headers,
        json=_payload(digest=encode_base64url(b"\x01" * 32)),
    )

    assert missing.status_code == 400
    assert valid.status_code == 201
    assert valid.get_json()["application"]["signing_certificate_sha256"]


def test_managed_application_list_and_update(app: Flask) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    headers = _authorization_header(token)
    client = app.test_client()
    created = client.post(
        "/api/v1/admin/applications",
        headers=headers,
        json=_payload(digest=encode_base64url(b"\x02" * 32)),
    )
    application_uuid = created.get_json()["application"]["application_uuid"]
    listed = client.get("/api/v1/admin/applications", headers=headers)
    updated_payload = _payload(digest=encode_base64url(b"\x03" * 32))
    updated_payload["display_name"] = "Updated learning app"
    updated = client.patch(
        f"/api/v1/admin/applications/{application_uuid}",
        headers=headers,
        json=updated_payload,
    )
    assert listed.status_code == 200
    assert len(listed.get_json()["applications"]) == 1
    assert updated.status_code == 200
    assert updated.get_json()["application"]["display_name"] == "Updated learning app"


@pytest.mark.parametrize("path", ["not-a-uuid", "00000000-0000-4000-8000-000000000000"])
def test_managed_application_update_rejects_invalid_or_missing_uuid(
    app: Flask, path: str
) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    response = app.test_client().patch(
        f"/api/v1/admin/applications/{path}",
        headers=_authorization_header(token),
        json=_payload(digest=encode_base64url(b"\x04" * 32)),
    )
    assert response.status_code in {400, 404}


def test_managed_application_rejects_duplicate_identity(app: Flask) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    client = app.test_client()
    payload = _payload(digest=encode_base64url(b"\x05" * 32))
    assert (
        client.post(
            "/api/v1/admin/applications",
            headers=_authorization_header(token),
            json=payload,
        ).status_code
        == 201
    )
    duplicate = client.post(
        "/api/v1/admin/applications", headers=_authorization_header(token), json=payload
    )
    assert duplicate.status_code == 409


def test_managed_application_rejects_malformed_payload(app: Flask) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    response = app.test_client().post(
        "/api/v1/admin/applications",
        headers=_authorization_header(token),
        json={"display_name": "missing fields"},
    )
    assert response.status_code == 400


def test_managed_application_handles_database_failure(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    monkeypatch.setattr(
        "app.routes.managed_applications.db.session.commit",
        lambda: (_ for _ in ()).throw(SQLAlchemyError("offline")),
    )
    response = app.test_client().post(
        "/api/v1/admin/applications",
        headers=_authorization_header(token),
        json=_payload(digest=encode_base64url(b"\x06" * 32)),
    )
    assert response.status_code == 503


def test_managed_application_update_handles_database_failure(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    client = app.test_client()
    created = client.post(
        "/api/v1/admin/applications",
        headers=_authorization_header(token),
        json=_payload(digest=encode_base64url(b"\x07" * 32)),
    )
    application_uuid = created.get_json()["application"]["application_uuid"]
    monkeypatch.setattr(
        "app.routes.managed_applications.db.session.commit",
        lambda: (_ for _ in ()).throw(SQLAlchemyError("offline")),
    )
    response = client.patch(
        f"/api/v1/admin/applications/{application_uuid}",
        headers=_authorization_header(token),
        json=_payload(digest=encode_base64url(b"\x08" * 32)),
    )
    assert response.status_code == 503


def test_managed_application_and_domain_payload_validation() -> None:
    with pytest.raises(ValueError):
        _parse_payload({})
    with pytest.raises(ValueError):
        _parse_payload({**_payload(digest=None), "signing_certificate_sha256": None})
    with pytest.raises(ValueError):
        _parse_payload(
            {
                **_payload(digest=encode_base64url(b"x" * 32)),
                "education_approved": "yes",
            }
        )
    parsed = _parse_payload(
        {
            **_payload(digest=encode_base64url(b"x" * 32)),
            "signing_certificate_sha256": None,
        },
        require_verified_identity=False,
    )
    assert parsed["signing_certificate_sha256"] is None
    assert decode_base64url(encode_base64url(b"x" * 32), decoded_length=32) == b"x" * 32
    with pytest.raises(ValueError):
        _parse_domain_payload({"domain": "example.org"})
    with pytest.raises(ValueError):
        _parse_domain_payload({"domain": 1, "category": "social", "status": "enabled"})
    assert (
        _parse_domain_payload(
            {"domain": "example.org", "category": " Social ", "status": "enabled"}
        )["category"]
        == "social"
    )


def test_managed_domain_catalogue_crud_and_database_failures(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    headers = _authorization_header(token)
    client = app.test_client()
    payload = {"domain": "example.org", "category": "education", "status": "enabled"}
    created = client.post("/api/v1/admin/domains", headers=headers, json=payload)
    assert created.status_code == 201
    domain_uuid = created.get_json()["domain"]["domain_uuid"]
    listed = client.get("/api/v1/admin/domains", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["domains"][0]["domain"] == "example.org"
    updated = client.patch(
        f"/api/v1/admin/domains/{domain_uuid}",
        headers=headers,
        json={
            "domain": "learning.example.org",
            "category": "learning",
            "status": "enabled",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["domain"]["domain"] == "learning.example.org"
    assert (
        client.patch(
            "/api/v1/admin/domains/not-a-uuid", headers=headers, json=payload
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/v1/admin/domains/{uuid4()}", headers=headers, json=payload
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/admin/domains", headers=headers, json={"domain": "broken"}
        ).status_code
        == 400
    )

    monkeypatch.setattr(
        "app.routes.managed_applications.db.session.commit",
        lambda: (_ for _ in ()).throw(SQLAlchemyError("offline")),
    )
    assert (
        client.post(
            "/api/v1/admin/domains",
            headers=headers,
            json={**payload, "domain": "offline.example.org"},
        ).status_code
        == 503
    )
