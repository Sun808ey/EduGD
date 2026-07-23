import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from flask import Flask
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.device_cryptography import (
    encode_base64url,
    enrollment_message,
    request_message,
    rotation_message,
)
from app.extensions import db
from app.models import (
    AdministratorPermission,
    Device,
    DeviceCredential,
    DeviceEnrollmentEvent,
    DeviceRequestNonce,
    EnrollmentToken,
)
from app.services.administrator_authentication import bootstrap_administrator

USERNAME = "device.enrollment.admin"
PASSWORD = "OfflineSchool!2026"
DEVICE_UUID = "550e8400-e29b-41d4-a716-446655440000"


def _bootstrap_and_login(app: Flask) -> str:
    with app.app_context():
        bootstrap_administrator(
            username=USERNAME,
            display_name="Device Enrollment Administrator",
            password=PASSWORD,
            operator_subject="test-operator",
            reason="device enrollment tests",
        )
    response = app.test_client().post(
        "/api/v1/admin/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    assert response.status_code == 200
    payload = cast(dict[str, Any], response.get_json())
    return cast(str, payload["access_token"])


def _issue_token(app: Flask, access_token: str, bound_uuid: str | None = None) -> str:
    payload: dict[str, str] = {"reason": "school-owned device provisioning"}
    if bound_uuid is not None:
        payload["bound_device_uuid"] = bound_uuid
    response = app.test_client().post(
        "/api/v1/admin/enrollment-tokens",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    response_payload = cast(dict[str, Any], response.get_json())
    return cast(str, response_payload["pairing_token"])


def _key_material() -> tuple[rsa.RSAPrivateKey, str, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, encode_base64url(der), hashlib.sha256(der).digest()


def _enrollment_payload(
    pairing_token: str,
    private_key: rsa.RSAPrivateKey,
    public_key: str,
    fingerprint: bytes,
) -> dict[str, Any]:
    token_uuid = pairing_token.split(".", 1)[0]
    nonce = encode_base64url(secrets.token_bytes(16))
    message = enrollment_message(
        device_uuid=DEVICE_UUID,
        token_uuid=token_uuid,
        algorithm="RSA_2048_SHA256",
        public_key_fingerprint=fingerprint,
        android_version="10",
        api_level=29,
        nonce=nonce,
    )
    proof = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    return {
        "device_uuid": DEVICE_UUID,
        "android_version": "10",
        "api_level": 29,
        "pairing_token": pairing_token,
        "credential": {
            "algorithm": "RSA_2048_SHA256",
            "public_key": public_key,
            "nonce": nonce,
            "proof": encode_base64url(proof),
        },
    }


def _signed_headers(
    private_key: rsa.RSAPrivateKey,
    credential_uuid: str,
    *,
    method: str = "GET",
    path: str | None = None,
    query: str = "",
    body: bytes = b"",
    nonce: str | None = None,
) -> tuple[dict[str, str], str]:
    path = path or f"/api/v1/sync/policies/{DEVICE_UUID}"
    nonce = nonce or encode_base64url(secrets.token_bytes(16))
    timestamp = str(int(datetime.now(UTC).timestamp()))
    body_hash = hashlib.sha256(body).hexdigest()
    message = request_message(
        method=method,
        canonical_path=path,
        canonical_query=query,
        body_hash=body_hash,
        timestamp=timestamp,
        nonce=nonce,
        credential_uuid=credential_uuid,
        device_uuid=DEVICE_UUID,
    )
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    return (
        {
            "Authorization": f"DeviceCredential {credential_uuid}",
            "X-Device-Timestamp": timestamp,
            "X-Device-Nonce": nonce,
            "X-Device-Body-SHA256": body_hash,
            "X-Device-Signature": encode_base64url(signature),
        },
        nonce,
    )


def _enroll(app: Flask) -> tuple[str, rsa.RSAPrivateKey, str]:
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    enrollment_payload = _enrollment_payload(
        pairing_token,
        private_key,
        public_key,
        fingerprint,
    )
    response = app.test_client().post(
        "/api/v1/devices/register",
        json=enrollment_payload,
    )
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    response_payload = cast(dict[str, Any], response.get_json())
    assert set(response_payload) == {
        "credential_algorithm",
        "credential_uuid",
        "device_status",
        "device_uuid",
        "enrollment_event_uuid",
        "server_time",
    }
    response_text = response.get_data(as_text=True)
    assert pairing_token not in response_text
    assert public_key not in response_text
    credential_payload = cast(dict[str, Any], enrollment_payload["credential"])
    assert cast(str, credential_payload["proof"]) not in response_text
    return cast(str, response_payload["credential_uuid"]), private_key, access_token


def test_enrollment_consumes_token_and_stores_only_public_credential(
    app: Flask,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, _ = _enroll(app)
    expected_public_key = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    expected_fingerprint = hashlib.sha256(expected_public_key).digest()

    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        credential = db.session.execute(select(DeviceCredential)).scalar_one()
        device = db.session.execute(select(Device)).scalar_one()
        success_event = db.session.execute(
            select(DeviceEnrollmentEvent).where(
                DeviceEnrollmentEvent.category == "enrollment_succeeded"
            )
        ).scalar_one()
        assert token.status == "consumed"
        assert len(token.verifier) == 32
        assert credential_uuid == str(credential.credential_uuid)
        assert UUID(credential_uuid).version == 4
        assert credential.enrollment_token_id == token.id
        assert credential.algorithm == "RSA_2048_SHA256"
        assert credential.status == "active"
        assert credential.public_key_der == expected_public_key
        assert credential.public_key_fingerprint == expected_fingerprint
        assert credential.last_used_at is None
        assert success_event.credential_id == credential.id
        assert success_event.token_id == token.id
        assert success_event.device_id == device.id
        assert success_event.public_key_fingerprint == expected_fingerprint
        assert "private_key" not in DeviceCredential.__table__.c
        assert "secret" not in DeviceCredential.__table__.c
        assert device.legacy_enrollment_eligible is False


def test_consumed_pairing_token_cannot_be_replayed(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    payload = _enrollment_payload(
        pairing_token,
        private_key,
        public_key,
        fingerprint,
    )

    enrolled = app.test_client().post("/api/v1/devices/register", json=payload)
    replayed = app.test_client().post("/api/v1/devices/register", json=payload)

    assert enrolled.status_code == 201
    assert replayed.status_code == 401
    assert replayed.get_json() == {"error": "enrollment_failed"}
    assert replayed.headers["Cache-Control"] == "no-store"
    assert pairing_token not in replayed.get_data(as_text=True)
    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        assert token.status == "consumed"
        assert len(db.session.execute(select(Device)).scalars().all()) == 1
        categories = list(
            db.session.execute(select(DeviceEnrollmentEvent.category)).scalars()
        )
        assert categories.count("token_consumed") == 1
        assert categories.count("enrollment_succeeded") == 1


def test_consumption_database_failure_rolls_back_without_consuming_token(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    payload = _enrollment_payload(
        pairing_token,
        private_key,
        public_key,
        fingerprint,
    )

    with app.app_context():
        original_commit = db.session.commit

        def fail_commit() -> None:
            raise SQLAlchemyError("forced enrollment commit failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        response = app.test_client().post("/api/v1/devices/register", json=payload)
        monkeypatch.setattr(db.session, "commit", original_commit)

        assert response.status_code == 500
        assert response.get_json() == {"error": "internal_server_error"}
        assert response.headers["Cache-Control"] == "no-store"
        assert pairing_token not in response.get_data(as_text=True)
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        assert token.status == "active"
        assert token.consumed_at is None
        assert token.consumed_by_device_id is None
        assert db.session.execute(select(Device)).scalar_one_or_none() is None
        assert (
            db.session.execute(select(DeviceCredential)).scalar_one_or_none() is None
        )
        categories = list(
            db.session.execute(select(DeviceEnrollmentEvent.category)).scalars()
        )
        assert categories == ["token_issued"]


def test_token_issuance_requires_administrator_permission(app: Flask) -> None:
    response = app.test_client().post(
        "/api/v1/admin/enrollment-tokens",
        json={"reason": "unauthorized request"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_failed"}
    with app.app_context():
        assert db.session.execute(select(EnrollmentToken)).scalar_one_or_none() is None


def test_invalid_proof_fails_generically_and_increments_attempt_count(
    app: Flask,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    payload = _enrollment_payload(pairing_token, private_key, public_key, fingerprint)
    payload["credential"]["proof"] = encode_base64url(b"x" * 256)

    response = app.test_client().post("/api/v1/devices/register", json=payload)

    assert response.status_code == 401
    assert response.get_json() == {"error": "enrollment_failed"}
    assert pairing_token not in response.get_data(as_text=True)
    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        assert token.failed_attempts == 1
        assert db.session.execute(select(Device)).scalar_one_or_none() is None


def test_altered_public_key_cannot_reuse_an_existing_proof(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    payload = _enrollment_payload(pairing_token, private_key, public_key, fingerprint)
    _, altered_public_key, _ = _key_material()
    payload["credential"]["public_key"] = altered_public_key

    response = app.test_client().post("/api/v1/devices/register", json=payload)

    assert response.status_code == 401
    assert response.get_json() == {"error": "enrollment_failed"}
    assert response.headers["Cache-Control"] == "no-store"
    assert altered_public_key not in response.get_data(as_text=True)
    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        failure = db.session.execute(
            select(DeviceEnrollmentEvent).where(
                DeviceEnrollmentEvent.category == "enrollment_failed"
            )
        ).scalar_one()
        assert token.status == "active"
        assert token.failed_attempts == 1
        assert failure.failure_class == "invalid_proof"
        assert db.session.execute(select(DeviceCredential)).scalar_one_or_none() is None
        assert db.session.execute(select(Device)).scalar_one_or_none() is None


def test_malformed_pairing_token_is_rejected_and_audited_without_identifier(
    app: Flask,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    payload = _enrollment_payload(
        pairing_token,
        private_key,
        public_key,
        fingerprint,
    )
    payload["pairing_token"] = "malformed-pairing-token"

    response = app.test_client().post("/api/v1/devices/register", json=payload)

    assert response.status_code == 401
    assert response.get_json() == {"error": "enrollment_failed"}
    assert response.headers["Cache-Control"] == "no-store"
    assert "malformed-pairing-token" not in response.get_data(as_text=True)
    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        assert token.status == "active"
        assert token.failed_attempts == 0
        failure = db.session.execute(
            select(DeviceEnrollmentEvent).where(
                DeviceEnrollmentEvent.category == "enrollment_failed"
            )
        ).scalar_one()
        assert failure.failure_class == "invalid_token"
        assert failure.token_id is None
        assert failure.device_id is None
        assert failure.credential_id is None
        assert db.session.execute(select(Device)).scalar_one_or_none() is None


def test_signed_sync_succeeds_and_replayed_nonce_fails(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, _ = _enroll(app)
    headers, nonce = _signed_headers(private_key, credential_uuid)
    target = f"/api/v1/sync/policies/{DEVICE_UUID}"

    success = app.test_client().get(
        target,
        headers=headers,
        environ_overrides={"RAW_URI": target},
    )
    replay = app.test_client().get(
        target,
        headers=headers,
        environ_overrides={"RAW_URI": target},
    )

    assert success.status_code == 200
    assert replay.status_code == 401
    assert replay.get_json() == {"error": "authentication_failed"}
    assert replay.headers["Cache-Control"] == "no-store"
    with app.app_context():
        credential = db.session.execute(select(DeviceCredential)).scalar_one()
        nonce_record = db.session.execute(select(DeviceRequestNonce)).scalar_one()
        categories = list(
            db.session.execute(select(DeviceEnrollmentEvent.category)).scalars()
        )
        assert credential.last_used_at is not None
        assert nonce_record.credential_id == credential.id
        assert len(nonce_record.nonce_hash) == 32
        assert nonce.encode() not in nonce_record.nonce_hash
        assert categories.count("authentication_succeeded") == 1
        assert categories.count("authentication_failed") == 1


def test_signed_raw_target_must_match_the_dispatched_route(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, _ = _enroll(app)
    route_path = f"/api/v1/sync/policies/{DEVICE_UUID}"
    signed_path = f"{route_path}/different-resource"
    headers, _ = _signed_headers(
        private_key,
        credential_uuid,
        path=signed_path,
    )

    response = app.test_client().get(
        route_path,
        headers=headers,
        environ_overrides={"RAW_URI": signed_path},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_failed"}
    assert response.headers["Cache-Control"] == "no-store"
    with app.app_context():
        failure = db.session.execute(
            select(DeviceEnrollmentEvent).where(
                DeviceEnrollmentEvent.category == "authentication_failed"
            )
        ).scalar_one()
        assert failure.failure_class == "invalid_signature"
        assert db.session.execute(select(DeviceRequestNonce)).scalar_one_or_none() is None


def test_enforcement_mode_rejects_missing_raw_request_target(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, _ = _enroll(app)
    path = f"/api/v1/sync/policies/{DEVICE_UUID}"
    headers, _ = _signed_headers(private_key, credential_uuid, path=path)
    app.config["TESTING"] = False

    response = app.test_client().get(
        path,
        headers=headers,
        environ_overrides={"RAW_URI": None, "REQUEST_URI": None},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_failed"}
    assert response.headers["Cache-Control"] == "no-store"


def test_uuid_only_sync_is_rejected_for_new_device(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    _enroll(app)

    response = app.test_client().get(f"/api/v1/sync/policies/{DEVICE_UUID}")

    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_failed"}


def test_administrator_revocation_immediately_blocks_sync(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, access_token = _enroll(app)
    reason = "device reported missing"
    revoke = app.test_client().post(
        f"/api/v1/admin/devices/{DEVICE_UUID}/credentials/revoke",
        json={"reason": reason},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    headers, _ = _signed_headers(private_key, credential_uuid)
    target = f"/api/v1/sync/policies/{DEVICE_UUID}"

    response = app.test_client().get(
        target,
        headers=headers,
        environ_overrides={"RAW_URI": target},
    )
    fallback_attempt = app.test_client().get(target)
    rotation_path = f"/api/v1/devices/{DEVICE_UUID}/credentials/rotate"
    rotation_body = b"{}"
    rotation_headers, _ = _signed_headers(
        private_key,
        credential_uuid,
        method="POST",
        path=rotation_path,
        body=rotation_body,
    )
    rotation_headers["Content-Type"] = "application/json"
    rotation = app.test_client().post(
        rotation_path,
        data=rotation_body,
        headers=rotation_headers,
        environ_overrides={"RAW_URI": rotation_path},
    )
    repeated = app.test_client().post(
        f"/api/v1/admin/devices/{DEVICE_UUID}/credentials/revoke",
        json={"reason": "duplicate request"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert revoke.status_code == 200
    assert revoke.get_json() == {"message": "device credential revoked"}
    assert revoke.headers["Cache-Control"] == "no-store"
    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_failed"}
    assert fallback_attempt.status_code == 401
    assert rotation.status_code == 401
    assert rotation.get_json() == {"error": "authentication_failed"}
    assert repeated.status_code == 404
    assert repeated.get_json() == {"error": "active_credential_not_found"}
    assert repeated.headers["Cache-Control"] == "no-store"
    with app.app_context():
        credential = db.session.execute(select(DeviceCredential)).scalar_one()
        event = db.session.execute(
            select(DeviceEnrollmentEvent).where(
                DeviceEnrollmentEvent.category == "credential_revoked"
            )
        ).scalar_one()
        assert credential.status == "revoked"
        assert credential.revoked_at is not None
        assert credential.revoked_by is not None
        assert credential.revocation_reason == reason
        assert credential.superseded_at is None
        assert credential.superseded_by_id is None
        assert event.event_uuid is not None
        assert event.device_id == credential.device_id
        assert event.credential_id == credential.id
        assert event.administrator_subject == credential.revoked_by
        assert event.reason == reason
        assert event.public_key_fingerprint == credential.public_key_fingerprint


def test_credential_revocation_requires_current_database_permission(
    app: Flask,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    _, _, access_token = _enroll(app)
    path = f"/api/v1/admin/devices/{DEVICE_UUID}/credentials/revoke"

    missing_authentication = app.test_client().post(
        path,
        json={"reason": "device reported missing"},
    )
    with app.app_context():
        permission = db.session.execute(
            select(AdministratorPermission).where(
                AdministratorPermission.permission == "device_credential.revoke"
            )
        ).scalar_one()
        db.session.delete(permission)
        db.session.commit()
    denied = app.test_client().post(
        path,
        json={"reason": "device reported missing"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert missing_authentication.status_code == 401
    assert missing_authentication.get_json() == {"error": "authentication_failed"}
    assert missing_authentication.headers["Cache-Control"] == "no-store"
    assert denied.status_code == 403
    assert denied.get_json() == {"error": "authorization_failed"}
    assert denied.headers["Cache-Control"] == "no-store"
    with app.app_context():
        credential = db.session.execute(select(DeviceCredential)).scalar_one()
        assert credential.status == "active"
        assert (
            db.session.execute(
                select(DeviceEnrollmentEvent).where(
                    DeviceEnrollmentEvent.category == "credential_revoked"
                )
            ).scalar_one_or_none()
            is None
        )


def test_credential_revocation_database_failure_rolls_back(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    _, _, access_token = _enroll(app)
    path = f"/api/v1/admin/devices/{DEVICE_UUID}/credentials/revoke"

    with app.app_context():
        original_commit = db.session.commit

        def fail_commit() -> None:
            raise SQLAlchemyError("forced credential revocation failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        response = app.test_client().post(
            path,
            json={"reason": "device reported missing"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        monkeypatch.setattr(db.session, "commit", original_commit)

        assert response.status_code == 500
        assert response.get_json() == {"error": "internal_server_error"}
        assert response.headers["Cache-Control"] == "no-store"
        credential = db.session.execute(select(DeviceCredential)).scalar_one()
        assert credential.status == "active"
        assert credential.revoked_at is None
        assert credential.revoked_by is None
        assert credential.revocation_reason is None
        assert (
            db.session.execute(
                select(DeviceEnrollmentEvent).where(
                    DeviceEnrollmentEvent.category == "credential_revoked"
                )
            ).scalar_one_or_none()
            is None
        )


def test_credential_rotation_requires_both_current_and_new_key_proof(
    app: Flask,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, old_private_key, _ = _enroll(app)
    new_private_key, new_public_key, fingerprint = _key_material()
    rotation_nonce = encode_base64url(secrets.token_bytes(16))
    proof_message = rotation_message(
        device_uuid=DEVICE_UUID,
        current_credential_uuid=credential_uuid,
        algorithm="RSA_2048_SHA256",
        public_key_fingerprint=fingerprint,
        nonce=rotation_nonce,
    )
    payload = {
        "algorithm": "RSA_2048_SHA256",
        "public_key": new_public_key,
        "nonce": rotation_nonce,
        "proof": encode_base64url(
            new_private_key.sign(
                proof_message,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        ),
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    path = f"/api/v1/devices/{DEVICE_UUID}/credentials/rotate"
    headers, _ = _signed_headers(
        old_private_key,
        credential_uuid,
        method="POST",
        path=path,
        body=body,
    )
    headers["Content-Type"] = "application/json"

    response = app.test_client().post(
        path,
        data=body,
        headers=headers,
        environ_overrides={"RAW_URI": path},
    )

    assert response.status_code == 201
    replacement_uuid = response.get_json()["credential_uuid"]
    new_headers, _ = _signed_headers(new_private_key, replacement_uuid)
    sync_path = f"/api/v1/sync/policies/{DEVICE_UUID}"
    assert (
        app.test_client()
        .get(
            sync_path,
            headers=new_headers,
            environ_overrides={"RAW_URI": sync_path},
        )
        .status_code
        == 200
    )


def test_revoked_pairing_token_cannot_enroll(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    token_uuid = pairing_token.split(".", 1)[0]
    revoke = app.test_client().post(
        f"/api/v1/admin/enrollment-tokens/{token_uuid}/revoke",
        json={"reason": "provisioning cancelled"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    private_key, public_key, fingerprint = _key_material()

    response = app.test_client().post(
        "/api/v1/devices/register",
        json=_enrollment_payload(
            pairing_token,
            private_key,
            public_key,
            fingerprint,
        ),
    )

    assert revoke.status_code == 200
    assert response.status_code == 401
    assert response.get_json() == {"error": "enrollment_failed"}


def test_signed_query_tampering_and_stale_timestamp_fail_closed(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, _ = _enroll(app)
    path = f"/api/v1/sync/policies/{DEVICE_UUID}"
    headers, _ = _signed_headers(
        private_key,
        credential_uuid,
        path=path,
        query="current_version=4",
    )
    tampered_target = f"{path}?current_version=5"
    tampered = app.test_client().get(
        tampered_target,
        headers=headers,
        environ_overrides={"RAW_URI": tampered_target},
    )
    stale_headers, _ = _signed_headers(private_key, credential_uuid, path=path)
    stale_headers["X-Device-Timestamp"] = "1000000000"
    stale = app.test_client().get(
        path,
        headers=stale_headers,
        environ_overrides={"RAW_URI": path},
    )

    assert tampered.status_code == 401
    assert stale.status_code == 401


def test_legacy_device_fallback_is_bounded_to_transition_eligible_rows(
    app: Flask,
) -> None:
    legacy_response = app.test_client().post(
        "/api/v1/devices/register",
        json={
            "device_uuid": DEVICE_UUID,
            "android_version": "10",
            "api_level": 29,
        },
    )
    assert legacy_response.status_code == 201
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"

    allowed = app.test_client().get(f"/api/v1/sync/policies/{DEVICE_UUID}")
    app.config["DEVICE_ENROLLMENT_MODE"] = "all_required"
    blocked = app.test_client().get(f"/api/v1/sync/policies/{DEVICE_UUID}")

    assert allowed.status_code == 200
    assert blocked.status_code == 401


def test_bound_recovery_token_replaces_a_revoked_credential(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    _, _, access_token = _enroll(app)
    revoke = app.test_client().post(
        f"/api/v1/admin/devices/{DEVICE_UUID}/credentials/revoke",
        json={"reason": "private key unavailable"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    pairing_token = _issue_token(app, access_token, DEVICE_UUID)
    private_key, public_key, fingerprint = _key_material()
    recovery = app.test_client().post(
        "/api/v1/devices/register",
        json=_enrollment_payload(
            pairing_token,
            private_key,
            public_key,
            fingerprint,
        ),
    )

    assert revoke.status_code == 200
    assert recovery.status_code == 201
    revoke_replacement = app.test_client().post(
        f"/api/v1/admin/devices/{DEVICE_UUID}/credentials/revoke",
        json={"reason": "replacement device retired"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    fallback = app.test_client().get(f"/api/v1/sync/policies/{DEVICE_UUID}")
    assert revoke_replacement.status_code == 200
    assert fallback.status_code == 401
    with app.app_context():
        statuses = list(
            db.session.execute(
                select(DeviceCredential.status).order_by(DeviceCredential.issued_at)
            ).scalars()
        )
        assert statuses == ["revoked", "revoked"]


def test_five_invalid_token_secrets_atomically_lock_pairing_token(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    token_uuid = pairing_token.split(".", 1)[0]
    private_key, public_key, fingerprint = _key_material()

    for _ in range(5):
        invalid_token = f"{token_uuid}.{encode_base64url(secrets.token_bytes(32))}"
        response = app.test_client().post(
            "/api/v1/devices/register",
            json=_enrollment_payload(
                invalid_token,
                private_key,
                public_key,
                fingerprint,
            ),
        )
        assert response.status_code == 401

    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        assert token.failed_attempts == 5
        assert token.status == "locked"


def test_legacy_mode_never_allows_uuid_only_credential_rotation(app: Flask) -> None:
    registration = app.test_client().post(
        "/api/v1/devices/register",
        json={
            "device_uuid": DEVICE_UUID,
            "android_version": "10",
            "api_level": 29,
        },
    )

    response = app.test_client().post(
        f"/api/v1/devices/{DEVICE_UUID}/credentials/rotate",
        json={"algorithm": "RSA_2048_SHA256"},
    )

    assert registration.status_code == 201
    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_failed"}


def test_administrator_enrollment_routes_use_bounded_error_contracts(
    app: Flask,
) -> None:
    access_token = _bootstrap_and_login(app)
    authorization = {"Authorization": f"Bearer {access_token}"}
    missing_uuid = str(uuid4())
    missing_bound = app.test_client().post(
        "/api/v1/admin/enrollment-tokens",
        json={"reason": "missing inventory", "bound_device_uuid": missing_uuid},
        headers=authorization,
    )
    missing_token = app.test_client().post(
        f"/api/v1/admin/enrollment-tokens/{missing_uuid}/revoke",
        json={"reason": "not present"},
        headers=authorization,
    )
    missing_credential = app.test_client().post(
        f"/api/v1/admin/devices/{missing_uuid}/credentials/revoke",
        json={"reason": "not present"},
        headers=authorization,
    )
    app.config["ENROLLMENT_ADMIN_ENABLED"] = False
    disabled = app.test_client().post(
        "/api/v1/admin/enrollment-tokens",
        json={"reason": "disabled operation"},
        headers=authorization,
    )

    assert missing_bound.status_code == 404
    assert missing_token.status_code == 404
    assert missing_credential.status_code == 404
    assert disabled.status_code == 409


def test_enrollment_schema_errors_are_generic_and_no_store(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    unsupported = app.test_client().post(
        "/api/v1/devices/register",
        data="not-json",
        content_type="text/plain",
    )
    malformed = app.test_client().post(
        "/api/v1/devices/register",
        data="{",
        content_type="application/json",
    )
    missing = app.test_client().post("/api/v1/devices/register", json={})

    assert unsupported.status_code == 415
    assert malformed.status_code == 400
    assert missing.status_code == 400
    assert all(
        response.get_json() == {"error": "invalid_request"}
        for response in (unsupported, malformed, missing)
    )
    assert all(
        response.headers["Cache-Control"] == "no-store"
        for response in (unsupported, malformed, missing)
    )


def test_expired_token_is_marked_expired_and_rejected(app: Flask) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    with app.app_context():
        token = db.session.execute(select(EnrollmentToken)).scalar_one()
        token.created_at = datetime.now(UTC) - timedelta(minutes=20)
        token.expires_at = datetime.now(UTC) - timedelta(minutes=10)
        db.session.commit()
    private_key, public_key, fingerprint = _key_material()

    response = app.test_client().post(
        "/api/v1/devices/register",
        json=_enrollment_payload(
            pairing_token,
            private_key,
            public_key,
            fingerprint,
        ),
    )

    assert response.status_code == 401
    with app.app_context():
        assert (
            db.session.execute(select(EnrollmentToken.status)).scalar_one() == "expired"
        )


def test_bound_token_cannot_claim_a_different_existing_identity(app: Flask) -> None:
    inventory_uuid = str(uuid4())
    registered = app.test_client().post(
        "/api/v1/devices/register",
        json={
            "device_uuid": inventory_uuid,
            "android_version": "10",
            "api_level": 29,
        },
    )
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token, inventory_uuid)
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    private_key, public_key, fingerprint = _key_material()

    response = app.test_client().post(
        "/api/v1/devices/register",
        json=_enrollment_payload(
            pairing_token,
            private_key,
            public_key,
            fingerprint,
        ),
    )

    assert registered.status_code == 201
    assert response.status_code == 401


def test_signed_request_rejects_unknown_query_body_hash_and_device_mismatch(
    app: Flask,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, _ = _enroll(app)
    path = f"/api/v1/sync/policies/{DEVICE_UUID}"
    headers, _ = _signed_headers(private_key, credential_uuid, path=path)
    headers["X-Device-Body-SHA256"] = "0" * 64
    bad_hash = app.test_client().get(
        path,
        headers=headers,
        environ_overrides={"RAW_URI": path},
    )
    query_headers, _ = _signed_headers(
        private_key,
        credential_uuid,
        path=path,
        query="unexpected=1",
    )
    query_target = f"{path}?unexpected=1"
    bad_query = app.test_client().get(
        query_target,
        headers=query_headers,
        environ_overrides={"RAW_URI": query_target},
    )
    other_path = f"/api/v1/sync/policies/{uuid4()}"
    mismatch_headers, _ = _signed_headers(
        private_key,
        credential_uuid,
        path=other_path,
    )
    mismatch = app.test_client().get(
        other_path,
        headers=mismatch_headers,
        environ_overrides={"RAW_URI": other_path},
    )

    assert bad_hash.status_code == 401
    assert bad_query.status_code == 401
    assert mismatch.status_code == 401


def test_signed_malformed_rotation_body_is_rejected_after_authentication(
    app: Flask,
) -> None:
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    credential_uuid, private_key, _ = _enroll(app)
    body = b"{}"
    path = f"/api/v1/devices/{DEVICE_UUID}/credentials/rotate"
    headers, _ = _signed_headers(
        private_key,
        credential_uuid,
        method="POST",
        path=path,
        body=body,
    )
    headers["Content-Type"] = "application/json"

    response = app.test_client().post(
        path,
        data=body,
        headers=headers,
        environ_overrides={"RAW_URI": path},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_request"}
