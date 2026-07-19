from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, Uuid
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex

from app.models import (
    DeviceCredential,
    DeviceEnrollmentEvent,
    DeviceRequestNonce,
    EnrollmentToken,
)


def _constraint_names(model: Any, constraint_type: type[Any]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def _index_names(model: Any) -> set[str]:
    return {
        index.name
        for index in model.__table__.indexes
        if isinstance(index, Index) and index.name is not None
    }


def test_enrollment_token_metadata_contract() -> None:
    table = EnrollmentToken.__table__

    assert table.c.id.primary_key is True
    assert isinstance(table.c.token_uuid.type, Uuid)
    assert table.c.token_uuid.type.as_uuid is True
    assert table.c.verifier.type.length == 32
    assert table.c.bound_device_id.nullable is True
    assert table.c.consumed_by_device_id.nullable is True
    assert table.c.issued_by.nullable is False
    assert table.c.reason.nullable is False
    assert {foreign_key.ondelete for foreign_key in table.foreign_keys} == {"RESTRICT"}
    assert _constraint_names(EnrollmentToken, UniqueConstraint) == {
        "uq_enrollment_tokens_uuid"
    }
    assert _constraint_names(EnrollmentToken, CheckConstraint) == {
        "ck_enrollment_tokens_consumption_state",
        "ck_enrollment_tokens_expiry",
        "ck_enrollment_tokens_failed_attempts",
        "ck_enrollment_tokens_pepper_version",
        "ck_enrollment_tokens_revocation_state",
        "ck_enrollment_tokens_status",
    }
    assert _index_names(EnrollmentToken) == {
        "ix_enrollment_tokens_bound_device",
        "ix_enrollment_tokens_status_expires",
    }
    assert "raw_token" not in table.c
    assert "token" not in table.c


def test_device_credential_metadata_contract() -> None:
    table = DeviceCredential.__table__

    assert isinstance(table.c.credential_uuid.type, Uuid)
    assert table.c.public_key_der.nullable is False
    assert table.c.public_key_fingerprint.type.length == 32
    assert table.c.device_id.nullable is False
    assert table.c.enrollment_token_id.nullable is True
    assert {foreign_key.ondelete for foreign_key in table.foreign_keys} == {"RESTRICT"}
    assert _constraint_names(DeviceCredential, UniqueConstraint) == {
        "uq_device_credentials_public_key_fingerprint",
        "uq_device_credentials_uuid",
    }
    assert _constraint_names(DeviceCredential, CheckConstraint) == {
        "ck_device_credentials_algorithm",
        "ck_device_credentials_lifecycle",
        "ck_device_credentials_status",
    }
    assert _index_names(DeviceCredential) == {
        "ix_device_credentials_device_status",
        "uq_device_credentials_active_device",
    }
    assert "private_key" not in table.c
    assert "secret" not in table.c

    active_index = next(
        index
        for index in table.indexes
        if index.name == "uq_device_credentials_active_device"
    )
    assert active_index.unique is True
    postgres_ddl = str(CreateIndex(active_index).compile(dialect=postgresql.dialect()))
    sqlite_ddl = str(CreateIndex(active_index).compile(dialect=sqlite.dialect()))
    assert "WHERE status = 'active'" in postgres_ddl
    assert "WHERE status = 'active'" in sqlite_ddl


def test_request_nonce_metadata_contract() -> None:
    table = DeviceRequestNonce.__table__

    assert table.c.credential_id.nullable is False
    assert table.c.nonce_hash.type.length == 32
    assert table.c.observed_at.nullable is False
    assert table.c.expires_at.nullable is False
    assert {foreign_key.ondelete for foreign_key in table.foreign_keys} == {"RESTRICT"}
    assert _constraint_names(DeviceRequestNonce, UniqueConstraint) == {
        "uq_device_request_nonces_credential_hash"
    }
    assert _constraint_names(DeviceRequestNonce, CheckConstraint) == {
        "ck_device_request_nonces_expiry"
    }
    assert _index_names(DeviceRequestNonce) == {"ix_device_request_nonces_expires_at"}
    assert "nonce" not in table.c


def test_enrollment_event_metadata_contract() -> None:
    table = DeviceEnrollmentEvent.__table__

    assert isinstance(table.c.event_uuid.type, Uuid)
    assert table.c.device_id.nullable is True
    assert table.c.credential_id.nullable is True
    assert table.c.token_id.nullable is True
    assert table.c.public_key_fingerprint.type.length == 32
    assert {foreign_key.ondelete for foreign_key in table.foreign_keys} == {"RESTRICT"}
    assert _constraint_names(DeviceEnrollmentEvent, UniqueConstraint) == {
        "uq_device_enrollment_events_uuid"
    }
    assert _constraint_names(DeviceEnrollmentEvent, CheckConstraint) == {
        "ck_device_enrollment_events_category"
    }
    assert _index_names(DeviceEnrollmentEvent) == {
        "ix_device_enrollment_events_credential_created",
        "ix_device_enrollment_events_device_created",
    }
    assert "pairing_token" not in table.c
    assert "signature" not in table.c
    assert "public_key_der" not in table.c


@pytest.mark.parametrize(
    ("model", "values", "message"),
    [
        (
            EnrollmentToken,
            {
                "verifier": b"short",
                "expires_at": datetime.now(UTC) + timedelta(minutes=10),
                "issued_by": "administrator",
                "reason": "provisioning",
            },
            "verifier must contain 32 bytes",
        ),
        (
            EnrollmentToken,
            {
                "verifier": b"v" * 32,
                "status": "unknown",
                "expires_at": datetime.now(UTC) + timedelta(minutes=10),
                "issued_by": "administrator",
                "reason": "provisioning",
            },
            "invalid enrollment token status",
        ),
        (
            DeviceCredential,
            {
                "device_id": 1,
                "algorithm": "unknown",
                "public_key_der": b"public",
                "public_key_fingerprint": b"f" * 32,
            },
            "invalid device credential algorithm",
        ),
        (
            DeviceCredential,
            {
                "device_id": 1,
                "algorithm": "RSA_2048_SHA256",
                "public_key_der": b"public",
                "public_key_fingerprint": b"short",
            },
            "public key fingerprint must contain 32 bytes",
        ),
        (
            DeviceRequestNonce,
            {
                "credential_id": 1,
                "nonce_hash": b"short",
                "expires_at": datetime.now(UTC) + timedelta(minutes=10),
            },
            "nonce hash must contain 32 bytes",
        ),
        (
            DeviceEnrollmentEvent,
            {"category": "unknown"},
            "invalid device enrollment event category",
        ),
        (
            DeviceEnrollmentEvent,
            {
                "category": "enrollment_succeeded",
                "public_key_fingerprint": b"short",
            },
            "public key fingerprint must contain 32 bytes",
        ),
    ],
)
def test_enrollment_models_reject_invalid_bounded_values(
    model: Any,
    values: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        model(**values)


def test_enrollment_models_generate_internal_uuids_without_storing_secrets() -> None:
    now = datetime.now(UTC)
    token = EnrollmentToken(
        token_uuid=uuid4(),
        verifier=b"v" * 32,
        expires_at=now + timedelta(minutes=10),
        issued_by="administrator",
        reason="provisioning",
    )
    credential = DeviceCredential(
        credential_uuid=uuid4(),
        device_id=1,
        algorithm="RSA_2048_SHA256",
        public_key_der=b"public-key-der",
        public_key_fingerprint=b"f" * 32,
    )
    event = DeviceEnrollmentEvent(
        event_uuid=uuid4(),
        category="enrollment_succeeded",
    )

    assert token.verifier == b"v" * 32
    assert credential.public_key_der == b"public-key-der"
    assert event.category == "enrollment_succeeded"
