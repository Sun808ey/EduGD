from copy import deepcopy
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app.device_audit_contract import (
    DeviceAuditContractError,
    build_audit_batch,
    build_audit_event,
    sign_audit_batch,
    verify_audit_batch,
)


def event(sequence: int, previous: str | None = None) -> dict[str, object]:
    return build_audit_event(
        event_uuid=str(uuid4()),
        sequence=sequence,
        occurred_at="2026-09-20T12:00:00Z",
        elapsed_realtime_ms=sequence * 1000,
        boot_count=3,
        event_code="policy_block",
        outcome="blocked",
        policy_uuid="11111111-1111-4111-8111-111111111111",
        revision_uuid="22222222-2222-4222-8222-222222222222",
        rule_id="blocked_games",
        metadata={"package_name": "com.example.game"},
        previous_event_hash=previous,
    )


def batch(algorithm: str = "ECDSA_P256_SHA256") -> dict[str, object]:
    first = event(1)
    second = event(2, first["event_hash"])
    return build_audit_batch(
        batch_uuid=str(uuid4()),
        device_uuid=str(uuid4()),
        credential_uuid=str(uuid4()),
        signature_algorithm=algorithm,
        events=[first, second],
    )


def test_event_hash_detects_changes() -> None:
    value = event(1)
    changed = deepcopy(value)
    changed["outcome"] = "allowed"
    with pytest.raises(DeviceAuditContractError, match="hash mismatch"):
        build_audit_batch(
            batch_uuid=str(uuid4()),
            device_uuid=str(uuid4()),
            credential_uuid=str(uuid4()),
            signature_algorithm="ECDSA_P256_SHA256",
            events=[changed],
        )


def test_batch_rejects_sequence_gap_and_chain_break() -> None:
    first = event(1)
    with pytest.raises(DeviceAuditContractError, match="sequence gap"):
        build_audit_batch(
            batch_uuid=str(uuid4()),
            device_uuid=str(uuid4()),
            credential_uuid=str(uuid4()),
            signature_algorithm="ECDSA_P256_SHA256",
            events=[first, event(3, first["event_hash"])],
        )
    with pytest.raises(DeviceAuditContractError, match="chain mismatch"):
        build_audit_batch(
            batch_uuid=str(uuid4()),
            device_uuid=str(uuid4()),
            credential_uuid=str(uuid4()),
            signature_algorithm="ECDSA_P256_SHA256",
            events=[first, event(2, "0" * 64)],
        )


@pytest.mark.parametrize("algorithm", ["ECDSA_P256_SHA256", "RSA_2048_SHA256"])
def test_batch_signature_verifies(algorithm: str) -> None:
    private_key = (
        ec.generate_private_key(ec.SECP256R1())
        if algorithm.startswith("ECDSA")
        else rsa.generate_private_key(public_exponent=65537, key_size=2048)
    )
    unsigned = batch(algorithm)
    signed = sign_audit_batch(unsigned, private_key)
    verified = verify_audit_batch(
        signed,
        private_key.public_key(),
        expected_previous_head=None,
        expected_first_sequence=1,
    )
    assert verified["final_head"] == unsigned["final_head"]
    assert verified["last_sequence"] == 2


def test_verification_rejects_wrong_stored_chain_state() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    signed = sign_audit_batch(batch(), private_key)
    with pytest.raises(DeviceAuditContractError, match="stored chain"):
        verify_audit_batch(
            signed,
            private_key.public_key(),
            expected_previous_head="0" * 64,
            expected_first_sequence=1,
        )
    with pytest.raises(DeviceAuditContractError, match="stored sequence"):
        verify_audit_batch(
            signed,
            private_key.public_key(),
            expected_previous_head=None,
            expected_first_sequence=2,
        )


def test_signature_detects_batch_tampering() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    signed = sign_audit_batch(batch(), private_key)
    changed = deepcopy(signed)
    changed["batch_uuid"] = str(uuid4())
    with pytest.raises(DeviceAuditContractError, match="signature"):
        verify_audit_batch(
            changed,
            private_key.public_key(),
            expected_previous_head=None,
            expected_first_sequence=1,
        )


def test_privacy_metadata_is_bounded_and_scalar_only() -> None:
    with pytest.raises(DeviceAuditContractError, match="metadata"):
        build_audit_event(
            event_uuid=str(uuid4()),
            sequence=1,
            occurred_at="2026-09-20T12:00:00Z",
            elapsed_realtime_ms=1,
            boot_count=1,
            event_code="policy_block",
            outcome="blocked",
            policy_uuid=None,
            revision_uuid=None,
            rule_id=None,
            metadata={"payload": {"nested": "content"}},
            previous_event_hash=None,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("event_uuid", 1),
        ("event_uuid", "not-a-uuid"),
        ("event_uuid", str(uuid4()).upper()),
        ("sequence", True),
        ("sequence", 0),
        ("occurred_at", 1),
        ("occurred_at", "not-a-timeZ"),
        ("occurred_at", "2026-09-20T12:00:00.100Z"),
        ("event_code", "unknown"),
        ("outcome", "unknown"),
        ("rule_id", "invalid rule"),
        ("policy_uuid", None),
        ("previous_event_hash", "short"),
        ("previous_event_hash", "Z" * 64),
        ("previous_event_hash", "A" * 64),
        ("metadata", {"invalid key": "value"}),
        ("metadata", {"payload": 2**64}),
        ("metadata", {"payload": "x" * 257}),
        ("metadata", {"payload": {"nested": "value"}}),
    ],
)
def test_event_rejects_invalid_identity_timing_and_metadata(
    field: str, value: object
) -> None:
    valid = event(1)
    valid.pop("event_hash")
    valid[field] = value
    with pytest.raises(DeviceAuditContractError):
        build_audit_event(**valid)


def test_event_rejects_extra_fields_and_unbounded_metadata() -> None:
    value = event(1)
    value["device_location"] = "private"
    with pytest.raises(DeviceAuditContractError, match="invalid audit event"):
        build_audit_batch(
            batch_uuid=str(uuid4()),
            device_uuid=str(uuid4()),
            credential_uuid=str(uuid4()),
            signature_algorithm="ECDSA_P256_SHA256",
            events=[value],
        )
    value.pop("device_location")
    value.pop("event_hash")
    value["metadata"] = {f"key_{index}": index for index in range(17)}
    with pytest.raises(DeviceAuditContractError, match="metadata"):
        build_audit_event(**value)


def test_batch_rejects_unsupported_algorithm_and_empty_events() -> None:
    valid = batch()
    valid["signature_algorithm"] = "none"
    with pytest.raises(DeviceAuditContractError, match="algorithm"):
        sign_audit_batch(valid, ec.generate_private_key(ec.SECP256R1()))
    with pytest.raises(DeviceAuditContractError, match="event batch"):
        build_audit_batch(
            batch_uuid=str(uuid4()),
            device_uuid=str(uuid4()),
            credential_uuid=str(uuid4()),
            signature_algorithm="ECDSA_P256_SHA256",
            events=[],
        )


@pytest.mark.parametrize(
    "field,value", [("protocol_version", 1), ("final_head", "0" * 64)]
)
def test_batch_rejects_protocol_or_chain_field_drift(field: str, value: object) -> None:
    valid = batch()
    valid[field] = value
    with pytest.raises(DeviceAuditContractError):
        sign_audit_batch(valid, ec.generate_private_key(ec.SECP256R1()))


def test_signing_rejects_wrong_key_algorithm() -> None:
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(DeviceAuditContractError, match="key"):
        sign_audit_batch(batch(), rsa_key)
    with pytest.raises(DeviceAuditContractError, match="key"):
        sign_audit_batch(
            batch("RSA_2048_SHA256"), ec.generate_private_key(ec.SECP256R1())
        )


@pytest.mark.parametrize("signature", [None, "not-base64!", "AA"])
def test_verification_rejects_malformed_signatures(signature: object) -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    signed = sign_audit_batch(batch(), private_key)
    signed["signature"] = signature
    with pytest.raises(DeviceAuditContractError, match="signature"):
        verify_audit_batch(
            signed,
            private_key.public_key(),
            expected_previous_head=None,
            expected_first_sequence=1,
        )
