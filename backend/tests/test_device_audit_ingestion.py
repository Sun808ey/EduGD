import json
from typing import Any, cast
from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import func, select

from app.device_audit_contract import (
    build_audit_batch,
    build_audit_event,
    sign_audit_batch,
)
from app.extensions import db
from app.models import (
    DeviceAuditBatch,
    DeviceAuditChainHead,
    DeviceAuditImmutableError,
    DeviceSecurityEvent,
)
from tests.test_device_enrollment_authentication import (
    DEVICE_UUID,
    _bootstrap_and_login,
    _enrollment_payload,
    _issue_token,
    _key_material,
    _signed_headers,
)


def _enroll_for_audit(app: Flask):
    app.config["DEVICE_ENROLLMENT_MODE"] = "new_devices_required"
    access_token = _bootstrap_and_login(app)
    pairing_token = _issue_token(app, access_token)
    private_key, public_key, fingerprint = _key_material()
    response = app.test_client().post(
        "/api/v1/devices/register",
        json=_enrollment_payload(pairing_token, private_key, public_key, fingerprint),
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()["credential_uuid"], private_key


def _signed_batch(private_key: Any, credential_uuid: str) -> dict[str, object]:
    first = build_audit_event(
        event_uuid=str(uuid4()),
        sequence=1,
        occurred_at="2026-09-20T12:00:00Z",
        elapsed_realtime_ms=10_000,
        boot_count=1,
        event_code="policy_block",
        outcome="blocked",
        policy_uuid=None,
        revision_uuid=None,
        rule_id="blocked_games",
        metadata={"package_name": "com.example.game"},
        previous_event_hash=None,
    )
    unsigned = build_audit_batch(
        batch_uuid=str(uuid4()),
        device_uuid=DEVICE_UUID,
        credential_uuid=credential_uuid,
        signature_algorithm="RSA_2048_SHA256",
        events=[first],
    )
    return sign_audit_batch(unsigned, private_key)


def _upload(app: Flask, private_key: Any, credential_uuid: str, payload: object):
    path = f"/api/v1/devices/{DEVICE_UUID}/audit-batches"
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers, _ = _signed_headers(
        private_key,
        credential_uuid,
        method="POST",
        path=path,
        body=body,
    )
    return app.test_client().post(
        path, data=body, content_type="application/json", headers=headers
    )


def test_authenticated_batch_is_stored_and_exact_replay_is_idempotent(
    app: Flask,
) -> None:
    credential_uuid, private_key = _enroll_for_audit(app)
    payload = _signed_batch(private_key, credential_uuid)

    response = _upload(app, private_key, credential_uuid, payload)
    assert response.status_code == 200
    result = cast(dict[str, Any], response.get_json())
    assert result["accepted_through_sequence"] == 1
    assert result["chain_head"] == payload["final_head"]
    assert result["replayed"] is False
    assert response.headers["Cache-Control"] == "no-store"

    replay = _upload(app, private_key, credential_uuid, payload)
    assert replay.status_code == 200
    assert cast(dict[str, Any], replay.get_json())["replayed"] is True

    with app.app_context():
        assert (
            db.session.scalar(select(func.count()).select_from(DeviceAuditBatch)) == 1
        )
        assert (
            db.session.scalar(select(func.count()).select_from(DeviceSecurityEvent))
            == 1
        )
        head = db.session.get(DeviceAuditChainHead, 1)
        assert head is not None
        assert head.last_sequence == 1
        assert head.head_event_hash.hex() == payload["final_head"]


def test_batch_rejects_tampering_without_storing_evidence(app: Flask) -> None:
    credential_uuid, private_key = _enroll_for_audit(app)
    payload = _signed_batch(private_key, credential_uuid)
    cast(dict[str, object], cast(list[object], payload["events"])[0])["outcome"] = (
        "allowed"
    )

    response = _upload(app, private_key, credential_uuid, payload)
    assert response.status_code == 400
    assert response.get_json() == {
        "error": {"code": "invalid_audit_batch", "message": "invalid audit batch"}
    }
    with app.app_context():
        assert (
            db.session.scalar(select(func.count()).select_from(DeviceAuditBatch)) == 0
        )
        assert (
            db.session.scalar(select(func.count()).select_from(DeviceSecurityEvent))
            == 0
        )


def test_second_batch_must_continue_stored_sequence_and_hash(app: Flask) -> None:
    credential_uuid, private_key = _enroll_for_audit(app)
    first = _signed_batch(private_key, credential_uuid)
    assert _upload(app, private_key, credential_uuid, first).status_code == 200

    disconnected = _signed_batch(private_key, credential_uuid)
    response = _upload(app, private_key, credential_uuid, disconnected)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_audit_batch"


def test_device_request_signature_is_required(app: Flask) -> None:
    credential_uuid, private_key = _enroll_for_audit(app)
    payload = _signed_batch(private_key, credential_uuid)
    response = app.test_client().post(
        f"/api/v1/devices/{DEVICE_UUID}/audit-batches", json=payload
    )
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"


def test_reused_batch_uuid_with_different_signed_content_is_rejected(
    app: Flask,
) -> None:
    credential_uuid, private_key = _enroll_for_audit(app)
    original = _signed_batch(private_key, credential_uuid)
    assert _upload(app, private_key, credential_uuid, original).status_code == 200

    replacement = _signed_batch(private_key, credential_uuid)
    replacement["batch_uuid"] = original["batch_uuid"]
    unsigned = {key: value for key, value in replacement.items() if key != "signature"}
    replacement = sign_audit_batch(unsigned, private_key)
    response = _upload(app, private_key, credential_uuid, replacement)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "audit_chain_conflict"


def test_stored_device_audit_evidence_is_immutable_in_orm(app: Flask) -> None:
    credential_uuid, private_key = _enroll_for_audit(app)
    assert (
        _upload(
            app,
            private_key,
            credential_uuid,
            _signed_batch(private_key, credential_uuid),
        ).status_code
        == 200
    )

    with app.app_context():
        event = db.session.execute(select(DeviceSecurityEvent)).scalar_one()
        event.outcome = "allowed"
        with pytest.raises(DeviceAuditImmutableError):
            db.session.commit()
        db.session.rollback()

        batch = db.session.execute(select(DeviceAuditBatch)).scalar_one()
        db.session.delete(batch)
        with pytest.raises(DeviceAuditImmutableError):
            db.session.commit()
        db.session.rollback()
