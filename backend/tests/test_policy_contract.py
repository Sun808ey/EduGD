from copy import deepcopy
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.policy_contract import (
    PolicyContractError,
    build_policy_envelope,
    canonical_json_bytes,
    policy_payload_hash,
    sign_policy_envelope,
    validate_policy_v2,
    verify_policy_envelope,
)


def policy() -> dict[str, object]:
    controls = {
        "camera_disabled": False,
        "screen_capture_disabled": True,
        "unknown_sources_disabled": True,
        "factory_reset_disabled": True,
        "safe_boot_disabled": True,
        "add_users_disabled": True,
        "account_changes_disabled": True,
        "usb_file_transfer_disabled": True,
    }
    return {
        "schema_version": 2,
        "timezone": "Africa/Kampala",
        "refresh_after_seconds": 3600,
        "default_mode": "class_hours",
        "emergency_packages": ["org.edug.dpc"],
        "required_capabilities": ["lock_task", "package_suspension"],
        "minimum_dpc_version": 1,
        "modes": [
            {
                "mode_id": "class_hours",
                "application_mode": "allowlist",
                "allowed_packages": ["org.edug.dpc", "org.example.learning"],
                "blocked_packages": ["com.example.game"],
                "lock_task_packages": ["org.example.learning"],
                "user_restrictions": ["disallow_install_unknown_sources"],
                "device_controls": controls,
            },
            {
                "mode_id": "night",
                "application_mode": "allowlist",
                "allowed_packages": ["org.edug.dpc"],
                "blocked_packages": ["com.example.game", "org.example.learning"],
                "lock_task_packages": [],
                "user_restrictions": ["disallow_install_unknown_sources"],
                "device_controls": controls,
            },
        ],
        "schedules": [
            {
                "schedule_id": "weekday_class",
                "days": [1, 2, 3, 4, 5],
                "start_minute": 480,
                "end_minute": 1020,
                "mode_id": "class_hours",
                "priority": 10,
            },
            {
                "schedule_id": "weekday_night",
                "days": [1, 2, 3, 4, 5],
                "start_minute": 1020,
                "end_minute": 480,
                "mode_id": "night",
                "priority": 10,
            },
        ],
    }


def test_policy_v2_normalizes_set_like_lists() -> None:
    value = policy()
    value["required_capabilities"] = ["package_suspension", "lock_task"]
    validated = validate_policy_v2(value)
    assert validated["required_capabilities"] == ["lock_task", "package_suspension"]
    assert policy_payload_hash(value) == policy_payload_hash(validated)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(schema_version=1),
        lambda p: p.update(timezone="UTC"),
        lambda p: p.update(refresh_after_seconds=299),
        lambda p: p.update(default_mode="missing"),
        lambda p: p.update(emergency_packages=[]),
        lambda p: p["modes"][0].update(application_mode="denylist"),
        lambda p: p["modes"][0].update(allowed_packages=["org.example.learning"]),
        lambda p: p["modes"][0].update(blocked_packages=["org.example.learning"]),
        lambda p: p["modes"][0].update(lock_task_packages=["com.example.other"]),
        lambda p: p["schedules"][0].update(mode_id="missing"),
        lambda p: p["schedules"][0].update(start_minute=480, end_minute=480),
    ],
)
def test_policy_v2_rejects_unsafe_or_unsupported_values(mutation) -> None:
    value = policy()
    mutation(value)
    with pytest.raises(PolicyContractError):
        validate_policy_v2(value)


def test_policy_v2_rejects_ambiguous_equal_priority_overlap() -> None:
    value = policy()
    value["schedules"].append(
        {
            "schedule_id": "overlap",
            "days": [1],
            "start_minute": 500,
            "end_minute": 600,
            "mode_id": "night",
            "priority": 10,
        }
    )
    with pytest.raises(PolicyContractError, match="ambiguous"):
        validate_policy_v2(value)


def test_canonical_json_rejects_floats_and_normalizes_unicode() -> None:
    assert canonical_json_bytes({"value": "e\u0301"}) == canonical_json_bytes(
        {"value": "\u00e9"}
    )
    with pytest.raises(PolicyContractError):
        canonical_json_bytes({"value": 1.5})


def test_policy_envelope_signs_and_verifies() -> None:
    private_key = Ed25519PrivateKey.generate()
    envelope = build_policy_envelope(
        policy_uuid=str(uuid4()),
        revision_uuid=str(uuid4()),
        revision_number=3,
        issued_at="2026-09-20T12:00:00Z",
        signing_key_id="policy-2026-01",
        payload=policy(),
    )
    signed = sign_policy_envelope(envelope, private_key)
    verified = verify_policy_envelope(signed, private_key.public_key())
    assert verified == envelope


def test_policy_envelope_detects_payload_tampering() -> None:
    private_key = Ed25519PrivateKey.generate()
    envelope = build_policy_envelope(
        policy_uuid=str(uuid4()),
        revision_uuid=str(uuid4()),
        revision_number=1,
        issued_at="2026-09-20T12:00:00Z",
        signing_key_id="policy-2026-01",
        payload=policy(),
    )
    signed = sign_policy_envelope(envelope, private_key)
    tampered = deepcopy(signed)
    tampered["payload"]["minimum_dpc_version"] = 2
    with pytest.raises(PolicyContractError, match="payload hash"):
        verify_policy_envelope(tampered, private_key.public_key())


def test_policy_envelope_rejects_noncanonical_timestamp_and_uuid() -> None:
    with pytest.raises(PolicyContractError):
        build_policy_envelope(
            policy_uuid=str(uuid4()).upper(),
            revision_uuid=str(uuid4()),
            revision_number=1,
            issued_at="2026-09-20T12:00:00.000Z",
            signing_key_id="policy",
            payload=policy(),
        )


def test_golden_vector_is_stable_and_verifiable() -> None:
    import base64
    import json
    from pathlib import Path

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    vector = json.loads(
        (Path(__file__).parent / "fixtures" / "policy_v2_golden_vector.json").read_text(
            encoding="utf-8"
        )
    )
    public_key = Ed25519PublicKey.from_public_bytes(
        base64.urlsafe_b64decode(vector["public_key_base64url"] + "==")
    )
    unsigned = verify_policy_envelope(vector["envelope"], public_key)
    canonical = (
        base64.urlsafe_b64encode(canonical_json_bytes(unsigned))
        .rstrip(b"=")
        .decode("ascii")
    )
    assert canonical == vector["canonical_envelope_base64url"]
    assert vector["algorithm"] == "Ed25519"
