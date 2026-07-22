import hashlib
import hmac
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from flask import Flask
from sqlalchemy import delete, func, select

from app.device_cryptography import encode_base64url, enrollment_message
from app.enrollment_schemas import DeviceEnrollmentData, EnrollmentCredentialData
from app.extensions import db
from app.models import (
    Device,
    DeviceCredential,
    DeviceEnrollmentEvent,
    EnrollmentToken,
    utc_now,
)
from app.services.device_enrollment import EnrollmentFailed, enroll_device
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

pytestmark = [pytest.mark.postgres, pytest.mark.concurrency]


def test_pairing_token_is_consumed_exactly_once_under_concurrency(
    postgres_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        postgres_app.config,
        "PAIRING_TOKEN_PEPPER",
        "postgres-concurrency-test-pairing-token-pepper",
    )
    approved = validate_postgres_test_environment(require_destructive=True)
    token_uuid = uuid4()
    device_uuid = uuid4()
    secret = secrets.token_bytes(32)
    with postgres_app.app_context():
        pepper = postgres_app.config["PAIRING_TOKEN_PEPPER"].encode()
        verifier = hmac.new(
            pepper,
            str(token_uuid).encode() + b"\x00" + secret,
            hashlib.sha256,
        ).digest()
        token = EnrollmentToken(
            token_uuid=token_uuid,
            verifier=verifier,
            expires_at=utc_now() + timedelta(minutes=10),
            issued_by="postgres-concurrency-test",
            reason="concurrent token consumption test",
        )
        db.session.add(token)
        db.session.commit()
        token_id = token.id
        with db.engine.connect() as connection:
            validate_connected_postgres_test_environment(
                connection,
                approved,
                require_destructive=True,
            )
        db.session.remove()

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint = hashlib.sha256(public_der).digest()
    nonce = encode_base64url(secrets.token_bytes(16))
    message = enrollment_message(
        device_uuid=str(device_uuid),
        token_uuid=str(token_uuid),
        algorithm="RSA_2048_SHA256",
        public_key_fingerprint=fingerprint,
        android_version="10",
        api_level=29,
        nonce=nonce,
    )
    data = DeviceEnrollmentData(
        str(device_uuid),
        "10",
        29,
        f"{token_uuid}.{encode_base64url(secret)}",
        EnrollmentCredentialData(
            "RSA_2048_SHA256",
            encode_base64url(public_der),
            nonce,
            encode_base64url(
                private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
            ),
        ),
    )

    def consume_once() -> str:
        with postgres_app.app_context():
            try:
                enroll_device(data)
                return "enrolled"
            except EnrollmentFailed:
                return "rejected"
            finally:
                db.session.remove()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: consume_once(), range(2)))
        assert sorted(results) == ["enrolled", "rejected"]
        with postgres_app.app_context():
            assert (
                db.session.scalar(
                    select(func.count())
                    .select_from(Device)
                    .where(Device.device_uuid == device_uuid)
                )
                == 1
            )
            assert (
                db.session.scalar(
                    select(func.count())
                    .select_from(DeviceCredential)
                    .join(Device)
                    .where(Device.device_uuid == device_uuid)
                )
                == 1
            )
            consumed_token = db.session.get(EnrollmentToken, token_id)
            assert consumed_token is not None
            assert consumed_token.status == "consumed"
            db.session.remove()
    finally:
        with postgres_app.app_context():
            stored_device_id = db.session.scalar(
                select(Device.id).where(Device.device_uuid == device_uuid)
            )
            if stored_device_id is not None:
                credential_ids = select(DeviceCredential.id).where(
                    DeviceCredential.device_id == stored_device_id
                )
                db.session.execute(
                    delete(DeviceEnrollmentEvent).where(
                        (DeviceEnrollmentEvent.device_id == stored_device_id)
                        | (DeviceEnrollmentEvent.token_id == token_id)
                    )
                )
                db.session.execute(
                    delete(DeviceCredential).where(
                        DeviceCredential.id.in_(credential_ids)
                    )
                )
            db.session.execute(
                delete(DeviceEnrollmentEvent).where(
                    DeviceEnrollmentEvent.token_id == token_id
                )
            )
            db.session.execute(
                delete(EnrollmentToken).where(EnrollmentToken.id == token_id)
            )
            if stored_device_id is not None:
                db.session.execute(delete(Device).where(Device.id == stored_device_id))
            db.session.commit()
            db.session.remove()
