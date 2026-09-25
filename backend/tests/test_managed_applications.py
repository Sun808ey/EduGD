from flask import Flask

from app.device_cryptography import encode_base64url
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
