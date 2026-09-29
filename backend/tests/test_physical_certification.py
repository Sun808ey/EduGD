from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.models import DeviceAuditImmutableError, DeviceCapabilityCertification
from app.physical_certification import (
    CertificationError,
    validate_profile_payload,
    verify_certification_record,
    verify_enrollment_match,
)
from app.policy_contract import canonical_json_bytes
from app.services.physical_certification import store_certification

NOW = "2026-09-21T12:00:00Z"
HEX = "a" * 64


def _sign(key: Ed25519PrivateKey, value: object) -> str:
    return base64.b64encode(key.sign(canonical_json_bytes(value))).decode("ascii")


def _record(challenge: bytes = b"x" * 32):
    verifier = Ed25519PrivateKey.generate()
    operators = {
        "operator-one": Ed25519PrivateKey.generate(),
        "operator-two": Ed25519PrivateKey.generate(),
    }
    identity = {
        "manufacturer": "Example OEM",
        "model": "Reference One",
        "product": "reference_one",
        "api_level": 29,
        "build_fingerprint": "oem/reference_one/release:10/ABC/123:user/release-keys",
        "security_patch": "2026-09-05",
        "carrier": "Test Carrier",
        "carrier_configuration_sha256": "9" * 64,
    }
    handlers = [
        {
            "role": role,
            "package": package,
            "component": component,
            "version": "10.1",
            "signing_sha256": digest,
        }
        for role, package, component, digest in (
            (
                "action_dial",
                "com.android.dialer",
                "com.android.dialer.DialtactsActivity",
                "b" * 64,
            ),
            (
                "action_call_emergency",
                "com.android.dialer",
                "com.android.dialer.EmergencyActivity",
                "b" * 64,
            ),
            (
                "default_dialer",
                "com.android.dialer",
                "com.android.dialer.DialtactsActivity",
                "b" * 64,
            ),
            (
                "emergency_information",
                "com.android.emergency",
                "com.android.emergency.EmergencyInfoActivity",
                "c" * 64,
            ),
        )
    ]
    receipt = {
        "challenge_sha256": sha256(challenge).hexdigest(),
        "identity_sha256": sha256(canonical_json_bytes(identity)).hexdigest(),
        "baseline_sha256": HEX,
        "chain_sha256": "d" * 64,
        "google_root_sha256": "e" * 64,
        "verified_at": NOW,
        "revocation_checked_at": NOW,
        "security_level": "TrustedEnvironment",
        "verified_boot": "Verified",
        "device_locked": True,
        "dpc_package": "io.github.sun808ey.edugd.dpc",
        "dpc_signing_sha256": "f" * 64,
        "play_device_integrity": True,
        "inventory_sha256": sha256(canonical_json_bytes(handlers)).hexdigest(),
    }
    receipt["verifier_signature"] = _sign(verifier, receipt)
    payload = {
        "identity": identity,
        "handlers": handlers,
        "system_dependencies": ["com.android.systemui"],
        "baseline_sha256": HEX,
        "baseline_inventory_sha256": sha256(canonical_json_bytes(handlers)).hexdigest(),
        "factory_reset_reference": True,
        "dpc_signing_sha256": "f" * 64,
        "attestation": receipt,
        "call_test": {
            "authorization_reference": "OEM carrier test authorization",
            "before": "PASS",
            "during": "PASS",
            "after": "PASS",
            "tested_at": NOW,
        },
        "procedure": "Operator-supervised, factory-reset physical handset test",
        "certified_at": NOW,
        "previous_record_hash": None,
    }
    approvals = [
        {
            "operator_id": identifier,
            "signed_at": NOW,
            "signature": _sign(
                key, {"payload": payload, "operator_id": identifier, "signed_at": NOW}
            ),
        }
        for identifier, key in operators.items()
    ]
    return {"payload": payload, "approvals": approvals}, verifier, operators


def _keys(verifier, operators):
    return verifier.public_key(), {
        name: key.public_key() for name, key in operators.items()
    }


def test_dual_approval_and_append_only_storage(app: Flask):
    record, verifier, operators = _record()
    verifier_key, operator_keys = _keys(verifier, operators)
    with app.app_context():
        stored = store_certification(
            record, verifier_key=verifier_key, operator_keys=operator_keys
        )
        assert stored.record_hash == sha256(canonical_json_bytes(record)).digest()
        assert (
            db.session.execute(select(DeviceCapabilityCertification)).scalar_one()
            is stored
        )
        stored.build_fingerprint = "tampered"
        with pytest.raises(DeviceAuditImmutableError):
            db.session.commit()
        db.session.rollback()


def test_two_distinct_signatures_and_verifier_receipt_required():
    record, verifier, operators = _record()
    verifier_key, operator_keys = _keys(verifier, operators)
    verify_certification_record(
        record, verifier_key=verifier_key, operator_keys=operator_keys
    )
    altered = deepcopy(record)
    altered["payload"]["identity"]["carrier"] = "Other Carrier"
    with pytest.raises(CertificationError):
        verify_certification_record(
            altered, verifier_key=verifier_key, operator_keys=operator_keys
        )
    altered = deepcopy(record)
    altered["approvals"][1] = deepcopy(altered["approvals"][0])
    with pytest.raises(CertificationError):
        verify_certification_record(
            altered, verifier_key=verifier_key, operator_keys=operator_keys
        )
    altered = deepcopy(record)
    altered["payload"]["attestation"]["verifier_signature"] = "AAAA"
    with pytest.raises(CertificationError):
        verify_certification_record(
            altered, verifier_key=verifier_key, operator_keys=operator_keys
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["identity"].update(api_level=28),
        lambda p: p.update(identity={}),
        lambda p: p["identity"].update(model=""),
        lambda p: p["identity"].update(security_patch="not-a-date"),
        lambda p: p["identity"].update(carrier_configuration_sha256="invalid"),
        lambda p: p.update(factory_reset_reference=False),
        lambda p: p.update(previous_record_hash="invalid"),
        lambda p: p["handlers"].pop(),
        lambda p: p["handlers"][0].pop("role"),
        lambda p: p["handlers"][1].update(role="action_dial"),
        lambda p: p["handlers"][0].update(package="invalid package"),
        lambda p: p["handlers"][0].update(component="invalid component"),
        lambda p: p["handlers"][0].update(signing_sha256="invalid"),
        lambda p: p.update(system_dependencies=[]),
        lambda p: p.update(system_dependencies=["com.android.systemui"] * 2),
        lambda p: p["attestation"].update(security_level="Software"),
        lambda p: p["attestation"].update(inventory_sha256="0" * 64),
        lambda p: p.update(call_test={}),
        lambda p: p["call_test"].update(during="NOT_VERIFIED"),
        lambda p: p["attestation"].update(device_locked=False),
        lambda p: p["attestation"].update(play_device_integrity=False),
        lambda p: p.update(certified_at="not-a-timeZ"),
    ],
)
def test_unsafe_profiles_cannot_be_certified(mutation):
    record, _, _ = _record()
    mutation(record["payload"])
    with pytest.raises(CertificationError):
        validate_profile_payload(record["payload"])


def test_fresh_enrollment_rejects_inventory_carrier_and_challenge_drift():
    from datetime import UTC, datetime

    challenge = b"x" * 32
    record, verifier, operators = _record(challenge)
    verifier_key, operator_keys = _keys(verifier, operators)
    verify_certification_record(
        record, verifier_key=verifier_key, operator_keys=operator_keys
    )
    payload = record["payload"]
    kwargs = {
        "identity": payload["identity"],
        "handlers": payload["handlers"],
        "dpc_signing_sha256": payload["dpc_signing_sha256"],
        "expected_challenge": challenge,
        "fresh_receipt": payload["attestation"],
        "verifier_key": verifier_key,
        "now": datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
    }
    verify_enrollment_match(record, **kwargs)
    with pytest.raises(CertificationError):
        verify_enrollment_match(record, **{**kwargs, "expected_challenge": b"y" * 32})
    with pytest.raises(CertificationError):
        verify_enrollment_match(
            record,
            **{**kwargs, "identity": {**payload["identity"], "carrier": "Changed"}},
        )
    with pytest.raises(CertificationError):
        verify_enrollment_match(record, **{**kwargs, "handlers": []})


def test_certification_storage_rejects_a_stale_chain_head(app: Flask):
    record, verifier, operators = _record()
    verifier_key, operator_keys = _keys(verifier, operators)
    with app.app_context():
        store_certification(
            record, verifier_key=verifier_key, operator_keys=operator_keys
        )
        with pytest.raises(CertificationError, match="chain head"):
            store_certification(
                record, verifier_key=verifier_key, operator_keys=operator_keys
            )
