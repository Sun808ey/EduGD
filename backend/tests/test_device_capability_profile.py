from copy import deepcopy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.android_integration_config import DPC_APPLICATION_ID, INITIAL_EDUCATIONAL_APPS
from app.device_capability_profile import (
    resolve_policy_for_device,
    validate_device_capability_profile,
)
from app.policy_contract import (
    PolicyContractError,
    build_policy_envelope,
    canonical_json_bytes,
    sign_policy_envelope,
    verify_policy_envelope,
)


def profile():
    return {
        "model": "AOSP emulator",
        "handlers": [
            {
                "role": "action_dial",
                "package": "com.android.dialer",
                "system_signed": True,
                "attested": True,
            },
            {
                "role": "action_call_emergency",
                "package": "com.android.dialer",
                "system_signed": True,
                "attested": True,
            },
            {
                "role": "default_dialer",
                "package": "com.android.dialer",
                "system_signed": True,
                "attested": True,
            },
            {
                "role": "emergency_information",
                "package": "com.android.emergency",
                "system_signed": True,
                "attested": True,
            },
        ],
        "system_dependencies": ["com.android.systemui"],
        "emergency_call_tested": True,
    }


def template():
    return {
        "schema_version": 2,
        "timezone": "Africa/Kampala",
        "refresh_after_seconds": 3600,
        "default_mode": "class_hours",
        "required_capabilities": ["lock_task"],
        "minimum_dpc_version": 1,
        "modes": [
            {
                "mode_id": "class_hours",
                "application_mode": "allowlist",
                "allowed_packages": ["com.google.android.apps.classroom"],
                "blocked_packages": [],
                "lock_task_packages": ["com.google.android.apps.classroom"],
                "user_restrictions": [],
                "device_controls": {
                    "camera_disabled": False,
                    "screen_capture_disabled": True,
                    "unknown_sources_disabled": True,
                    "factory_reset_disabled": True,
                    "safe_boot_disabled": True,
                    "add_users_disabled": True,
                    "account_changes_disabled": True,
                    "usb_file_transfer_disabled": True,
                },
            }
        ],
        "schedules": [],
    }


VERIFIED = {(handler["role"], handler["package"]) for handler in profile()["handlers"]}

INSTALLED = {
    DPC_APPLICATION_ID,
    *INITIAL_EDUCATIONAL_APPS,
    "com.android.systemui",
    "com.android.dialer",
    "com.android.emergency",
}


def test_resolution_is_device_specific_canonical_and_signed():
    resolved = resolve_policy_for_device(
        template(),
        profile(),
        installed_packages=INSTALLED,
        verified_handlers=VERIFIED,
    )
    allowed = resolved["modes"][0]["allowed_packages"]
    locked = resolved["modes"][0]["lock_task_packages"]
    assert set(locked) <= set(allowed)
    assert {
        DPC_APPLICATION_ID,
        "com.android.systemui",
        "com.android.dialer",
        "com.android.emergency",
    } <= set(locked)
    assert "com.google.android.dialer" not in allowed
    assert canonical_json_bytes(resolved) == canonical_json_bytes(
        resolve_policy_for_device(
            template(),
            profile(),
            installed_packages=INSTALLED,
            verified_handlers=VERIFIED,
        )
    )
    key = Ed25519PrivateKey.generate()
    envelope = build_policy_envelope(
        policy_uuid="11111111-1111-4111-8111-111111111111",
        revision_uuid="22222222-2222-4222-8222-222222222222",
        revision_number=1,
        issued_at="2026-09-21T12:00:00Z",
        signing_key_id="pilot-test",
        payload=resolved,
    )
    signed = sign_policy_envelope(envelope, key)
    assert verify_policy_envelope(signed, key.public_key()) == envelope
    signed["payload"]["modes"][0]["allowed_packages"].append("com.android.settings")
    with pytest.raises(PolicyContractError):
        verify_policy_envelope(signed, key.public_key())


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(emergency_call_tested=False),
        lambda p: p["handlers"].pop(),
        lambda p: p["handlers"][0].update(attested=False),
        lambda p: p["handlers"][0].update(system_signed=False),
        lambda p: p["handlers"][1].update(role="action_dial"),
        lambda p: p["system_dependencies"].append("com.android.systemui"),
    ],
)
def test_unverified_or_duplicate_discovery_rejected(mutation):
    value = profile()
    mutation(value)
    with pytest.raises(PolicyContractError):
        validate_device_capability_profile(value, verified_handlers=VERIFIED)


def test_unknown_and_forbidden_packages_fail_closed():
    value = template()
    value["modes"][0]["allowed_packages"].append("com.android.settings")
    with pytest.raises(PolicyContractError):
        resolve_policy_for_device(
            value,
            profile(),
            installed_packages=INSTALLED | {"com.android.settings"},
            verified_handlers=VERIFIED,
        )
    value = template()
    value["modes"][0]["allowed_packages"].append("org.unknown.app")
    with pytest.raises(PolicyContractError):
        resolve_policy_for_device(
            value, profile(), installed_packages=INSTALLED, verified_handlers=VERIFIED
        )
    value = template()
    value["modes"][0]["allowed_packages"].append("com.google.android.apps.classroom")
    with pytest.raises(PolicyContractError):
        resolve_policy_for_device(
            value, profile(), installed_packages=INSTALLED, verified_handlers=VERIFIED
        )
    value = deepcopy(template())
    value["modes"][0]["blocked_packages"] = ["com.android.dialer"]
    with pytest.raises(PolicyContractError):
        resolve_policy_for_device(
            value, profile(), installed_packages=INSTALLED, verified_handlers=VERIFIED
        )
