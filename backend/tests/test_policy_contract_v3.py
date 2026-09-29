import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.policy_contract import PolicyContractError
from app.policy_contract_v3 import (
    normalize_domain,
    validate_policy_v3,
    verify_policy_v3_envelope,
)


def policy() -> dict[str, object]:
    controls = {
        "camera_disabled": False,
        "screen_capture_disabled": False,
        "unknown_sources_disabled": True,
        "factory_reset_disabled": True,
        "safe_boot_disabled": True,
        "add_users_disabled": True,
        "account_changes_disabled": True,
        "usb_file_transfer_disabled": True,
    }
    return {
        "schema_version": 3,
        "timezone": "Africa/Kampala",
        "refresh_after_seconds": 300,
        "default_mode": "school",
        "emergency_packages": ["org.edug.dpc"],
        "required_capabilities": ["screen_time", "web_filter"],
        "minimum_dpc_version": 3,
        "modes": [
            {
                "mode_id": "school",
                "application_mode": "allowlist",
                "allowed_packages": ["org.edug.dpc"],
                "blocked_packages": [],
                "lock_task_packages": [],
                "user_restrictions": [],
                "device_controls": controls,
            }
        ],
        "schedules": [],
        "screen_time": {
            "daily_limit_minutes": 120,
            "reset_minute": 0,
            "exhausted_mode_id": "school",
        },
        "web_filter": {
            "default_action": "allow",
            "rules": [
                {
                    "rule_id": "social",
                    "domain": "Example.COM.",
                    "include_subdomains": True,
                    "action": "block",
                    "reason": "focus",
                }
            ],
        },
        "network_controls": {
            "wifi_only": True,
            "disallow_mobile_network_configuration": True,
            "disallow_tethering": True,
            "disallow_user_vpn": True,
            "always_on_filtering_vpn": True,
            "vpn_lockdown_required": True,
        },
        "telephony_controls": {
            "disallow_outgoing_calls": True,
            "disallow_sms": True,
            "preserve_emergency_calls": True,
        },
    }


def test_v3_normalizes_domain_rules() -> None:
    result = validate_policy_v3(policy())
    assert result["schema_version"] == 3
    assert result["web_filter"]["rules"][0]["domain"] == "example.com"
    assert result["web_filter"]["rules"][0]["include_subdomains"] is True


@pytest.mark.parametrize("default_action", ["allow", "block"])
def test_v3_supports_both_web_filter_defaults(default_action: str) -> None:
    value = policy()
    value["web_filter"]["default_action"] = default_action

    assert validate_policy_v3(value)["web_filter"]["default_action"] == default_action


def test_v3_rejects_web_filter_rule_without_subdomain_semantics() -> None:
    value = policy()
    del value["web_filter"]["rules"][0]["include_subdomains"]

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


@pytest.mark.parametrize(
    "value", ["https://example.com", "example.com/path", "localhost", " bad.example"]
)
def test_domain_normalization_rejects_urls_and_invalid_hosts(value: str) -> None:
    with pytest.raises(PolicyContractError):
        normalize_domain(value)


def test_v3_requires_existing_exhausted_mode() -> None:
    value = policy()
    value["screen_time"]["exhausted_mode_id"] = "missing"
    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("network_controls", "always_on_filtering_vpn"),
        ("telephony_controls", "preserve_emergency_calls"),
    ],
)
def test_v3_rejects_unsafe_network_or_telephony_controls(
    section: str, field: str
) -> None:
    value = policy()
    value[section][field] = False

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


def test_v3_golden_vector_is_reproducible_without_private_key() -> None:
    vector = json.loads(
        (
            Path(__file__).parent / "fixtures" / "policy_v3_golden_vector.json"
        ).read_text()
    )
    public_key = Ed25519PublicKey.from_public_bytes(
        base64.urlsafe_b64decode(vector["public_key_base64url"] + "==")
    )

    verified = verify_policy_v3_envelope(vector["envelope"], public_key)

    assert verified == {
        key: value for key, value in vector["envelope"].items() if key != "signature"
    }
