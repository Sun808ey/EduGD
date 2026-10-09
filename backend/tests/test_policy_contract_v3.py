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
    assert result["schedules"] == []
    assert result["web_filter"]["rules"][0]["domain"] == "example.com"
    assert result["web_filter"]["rules"][0]["include_subdomains"] is True


def test_v3_accepts_recurring_time_based_schedules() -> None:
    value = policy()
    value["schedules"] = [
        {
            "schedule_id": "school_hours",
            "days": [1, 2, 3, 4, 5],
            "start_minute": 420,
            "end_minute": 1080,
            "mode_id": "school",
            "priority": 1,
        }
    ]

    result = validate_policy_v3(value)
    assert result["schedules"][0]["days"] == [1, 2, 3, 4, 5]
    assert result["schedules"][0]["start_minute"] == 420


def test_v3_validates_compliance_settings() -> None:
    value = policy()
    value["compliance_settings"] = {
        "device_enrolled": True,
        "dpc_active": True,
        "policy_version_current": True,
        "approved_learning_application_installed": True,
        "kiosk_mode_active": True,
        "unknown_sources_blocked": True,
        "factory_reset_restriction_active": True,
        "required_restrictions_applied": True,
        "connection_review_after_days": 3,
    }

    result = validate_policy_v3(value)

    assert result["compliance_settings"] == value["compliance_settings"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["compliance_settings"].pop("dpc_active"),
        lambda value: value["compliance_settings"].update(
            required_restrictions_applied="true"
        ),
        lambda value: value["compliance_settings"].update(
            connection_review_after_days=31
        ),
    ],
)
def test_v3_rejects_invalid_compliance_settings(mutation) -> None:
    value = policy()
    value["compliance_settings"] = {
        "device_enrolled": True,
        "dpc_active": True,
        "policy_version_current": True,
        "approved_learning_application_installed": True,
        "kiosk_mode_active": True,
        "unknown_sources_blocked": True,
        "factory_reset_restriction_active": True,
        "required_restrictions_applied": True,
        "connection_review_after_days": 3,
    }
    mutation(value)

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


def test_v3_validates_fail_safe_offline_settings() -> None:
    value = policy()
    value["offline_settings"] = {
        "enforce_last_valid_policy_offline": True,
        "store_local_policy_copy": True,
        "queue_events_while_offline": True,
        "apply_policy_changes_after_reconnection": True,
        "expire_policy_when_offline": False,
    }

    result = validate_policy_v3(value)

    assert result["offline_settings"] == value["offline_settings"]


def test_v3_validates_bounded_administrator_notes() -> None:
    value = policy()
    value["administrator_notes"] = "First line.\r\nSecond line."

    result = validate_policy_v3(value)

    assert result["administrator_notes"] == "First line.\nSecond line."


def test_v3_validates_management_only_data_collection() -> None:
    value = policy()
    value["data_collection_settings"] = {
        "store_device_asset_number": True,
        "store_device_policy_version": True,
        "store_last_synchronisation_time": True,
        "store_compliance_result": True,
        "store_administrative_actions": True,
        "collect_learner_location": False,
        "read_private_messages": False,
        "read_photographs": False,
        "record_microphone": False,
        "store_browsing_history": False,
    }

    result = validate_policy_v3(value)

    assert result["data_collection_settings"] == value["data_collection_settings"]


@pytest.mark.parametrize(
    "field,invalid_value",
    [
        ("store_device_asset_number", False),
        ("collect_learner_location", True),
        ("read_private_messages", True),
        ("read_photographs", True),
        ("record_microphone", True),
        ("store_browsing_history", True),
    ],
)
def test_v3_rejects_surveillance_or_missing_management_collection(
    field: str, invalid_value: bool
) -> None:
    value = policy()
    value["data_collection_settings"] = {
        "store_device_asset_number": True,
        "store_device_policy_version": True,
        "store_last_synchronisation_time": True,
        "store_compliance_result": True,
        "store_administrative_actions": True,
        "collect_learner_location": False,
        "read_private_messages": False,
        "read_photographs": False,
        "record_microphone": False,
        "store_browsing_history": False,
    }
    value["data_collection_settings"][field] = invalid_value

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


@pytest.mark.parametrize(
    "notes",
    ["", "x" * 2001, "not\x00printable"],
)
def test_v3_rejects_invalid_administrator_notes(notes: str) -> None:
    value = policy()
    value["administrator_notes"] = notes

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


@pytest.mark.parametrize(
    "field,invalid_value",
    [
        ("enforce_last_valid_policy_offline", False),
        ("store_local_policy_copy", False),
        ("queue_events_while_offline", False),
        ("apply_policy_changes_after_reconnection", False),
        ("expire_policy_when_offline", True),
    ],
)
def test_v3_rejects_unsafe_offline_setting(field: str, invalid_value: bool) -> None:
    value = policy()
    value["offline_settings"] = {
        "enforce_last_valid_policy_offline": True,
        "store_local_policy_copy": True,
        "queue_events_while_offline": True,
        "apply_policy_changes_after_reconnection": True,
        "expire_policy_when_offline": False,
    }
    value["offline_settings"][field] = invalid_value

    with pytest.raises(PolicyContractError, match="offline policy expiry"):
        validate_policy_v3(value)


def test_v3_validates_device_use_settings() -> None:
    value = policy()
    value["device_use"] = {
        "mode": "dedicated_learning",
        "kiosk_mode_enabled": False,
        "display_school_name": True,
        "school_name": "Example Secondary School",
        "support_message": "Contact the ICT office",
    }

    result = validate_policy_v3(value)

    assert result["device_use"] == value["device_use"]


def test_v3_validates_policy_identity_and_kiosk_invariants() -> None:
    value = policy()
    value["policy_code"] = "LEARNING_DEVICE"
    value["description"] = "Controls tablets used for classroom learning."
    value["device_use"] = {
        "mode": "dedicated_learning",
        "kiosk_mode_enabled": True,
        "display_school_name": True,
        "school_name": None,
        "support_message": "Contact the ICT office",
    }
    value["approved_applications"] = [
        {
            "application_uuid": "11111111-1111-4111-8111-111111111111",
            "display_name": "Learning app",
            "package_name": "org.example.learning",
            "application_type": "learning_application",
            "required": True,
            "allow_in_kiosk": True,
        }
    ]
    value["emergency_packages"] = ["io.github.sun808ey.edugd.dpc"]
    value["modes"][0]["allowed_packages"] = ["io.github.sun808ey.edugd.dpc"]

    result = validate_policy_v3(value)

    assert result["policy_code"] == "LEARNING_DEVICE"
    assert result["description"] == "Controls tablets used for classroom learning."


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(policy_code="bad-code"),
        lambda value: value.update(description="\x00"),
    ],
)
def test_v3_rejects_invalid_policy_identity(mutation) -> None:
    value = policy()
    value["policy_code"] = "LEARNING_DEVICE"
    value["description"] = "Valid description"
    mutation(value)

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


def test_v3_rejects_examination_mode_without_required_controls() -> None:
    value = policy()
    value["device_use"] = {
        "mode": "examination",
        "kiosk_mode_enabled": False,
        "display_school_name": True,
        "school_name": None,
        "support_message": "Contact the ICT office",
    }
    value["device_restrictions"] = {
        "block_factory_reset": True,
        "block_safe_mode": True,
        "block_developer_options_and_debugging": True,
        "block_usb_file_transfer": True,
        "block_account_changes": True,
        "block_user_switching": True,
        "block_network_reset": True,
        "block_wifi_changes": False,
        "disable_screenshots": False,
        "disable_screen_recording": False,
        "disable_camera": False,
        "disable_microphone": False,
        "disable_location": False,
    }

    with pytest.raises(PolicyContractError, match="examination mode"):
        validate_policy_v3(value)


def test_v3_validates_and_sorts_approved_applications() -> None:
    value = policy()
    value["approved_applications"] = [
        {
            "application_uuid": "22222222-2222-4222-8222-222222222222",
            "display_name": "Calculator",
            "package_name": "org.example.calculator",
            "application_type": "calculator",
            "required": False,
            "allow_in_kiosk": True,
        },
        {
            "application_uuid": "11111111-1111-4111-8111-111111111111",
            "display_name": "Learning app",
            "package_name": "org.example.learning",
            "application_type": "learning_application",
            "required": True,
            "allow_in_kiosk": True,
        },
    ]

    result = validate_policy_v3(value)

    assert [item["package_name"] for item in result["approved_applications"]] == [
        "org.example.calculator",
        "org.example.learning",
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["approved_applications"].clear(),
        lambda value: value["approved_applications"].append(
            {
                "application_uuid": "11111111-1111-4111-8111-111111111111",
                "display_name": "Duplicate package",
                "package_name": "org.example.learning",
                "application_type": "learning_application",
                "required": False,
                "allow_in_kiosk": True,
            }
        ),
        lambda value: value["approved_applications"][0].update(
            application_type="unapproved_type"
        ),
    ],
)
def test_v3_rejects_invalid_approved_applications(mutation) -> None:
    value = policy()
    value["approved_applications"] = [
        {
            "application_uuid": "11111111-1111-4111-8111-111111111111",
            "display_name": "Learning app",
            "package_name": "org.example.learning",
            "application_type": "learning_application",
            "required": True,
            "allow_in_kiosk": True,
        }
    ]
    mutation(value)

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


def test_v3_validates_application_controls_and_materialized_packages() -> None:
    value = policy()
    value["application_controls"] = {
        "allow_installation_of_other_applications": False,
        "allow_installation_from_unknown_sources": False,
        "allow_uninstall_of_approved_applications": False,
        "allow_disable_of_approved_applications": False,
        "allow_google_play_store": False,
        "allow_file_sharing_applications": False,
        "file_sharing_packages": ["com.example.fileshare"],
    }

    result = validate_policy_v3(value)

    assert result["application_controls"] == value["application_controls"]


def test_v3_validates_device_restrictions() -> None:
    value = policy()
    value["device_restrictions"] = {
        "block_factory_reset": True,
        "block_safe_mode": True,
        "block_developer_options_and_debugging": True,
        "block_usb_file_transfer": True,
        "block_account_changes": True,
        "block_user_switching": True,
        "block_network_reset": False,
        "block_wifi_changes": False,
        "disable_screenshots": False,
        "disable_screen_recording": False,
        "disable_camera": False,
        "disable_microphone": False,
        "disable_location": False,
    }

    result = validate_policy_v3(value)

    assert result["device_restrictions"] == value["device_restrictions"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["device_restrictions"].pop("block_wifi_changes"),
        lambda value: value["device_restrictions"].update(disable_camera="false"),
    ],
)
def test_v3_rejects_invalid_device_restrictions(mutation) -> None:
    value = policy()
    value["device_restrictions"] = {
        "block_factory_reset": True,
        "block_safe_mode": True,
        "block_developer_options_and_debugging": True,
        "block_usb_file_transfer": True,
        "block_account_changes": True,
        "block_user_switching": True,
        "block_network_reset": False,
        "block_wifi_changes": False,
        "disable_screenshots": False,
        "disable_screen_recording": False,
        "disable_camera": False,
        "disable_microphone": False,
        "disable_location": False,
    }
    mutation(value)

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


def test_v3_validates_screen_lock_defaults() -> None:
    value = policy()
    value["screen_lock"] = {
        "require_screen_lock": True,
        "automatic_lock_after_minutes": 5,
        "allow_biometric_unlock": False,
        "allow_learner_change_lock_method": False,
    }

    result = validate_policy_v3(value)

    assert result["screen_lock"] == value["screen_lock"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["screen_lock"].update(automatic_lock_after_minutes=2),
        lambda value: value["screen_lock"].update(allow_biometric_unlock="false"),
    ],
)
def test_v3_rejects_invalid_screen_lock(mutation) -> None:
    value = policy()
    value["screen_lock"] = {
        "require_screen_lock": True,
        "automatic_lock_after_minutes": 5,
        "allow_biometric_unlock": False,
        "allow_learner_change_lock_method": False,
    }
    mutation(value)

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["application_controls"].update(
            allow_google_play_store="false"
        ),
        lambda value: value["application_controls"].update(
            file_sharing_packages=["not-a-package"]
        ),
    ],
)
def test_v3_rejects_invalid_application_controls(mutation) -> None:
    value = policy()
    value["application_controls"] = {
        "allow_installation_of_other_applications": False,
        "allow_installation_from_unknown_sources": False,
        "allow_uninstall_of_approved_applications": False,
        "allow_disable_of_approved_applications": False,
        "allow_google_play_store": False,
        "allow_file_sharing_applications": False,
        "file_sharing_packages": [],
    }
    mutation(value)

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["device_use"].update(mode="unsupported"),
        lambda value: value["device_use"].update(support_message="\n"),
        lambda value: value["device_use"].update(
            display_school_name=False, school_name="Example Secondary School"
        ),
    ],
)
def test_v3_rejects_invalid_device_use_settings(mutation) -> None:
    value = policy()
    value["device_use"] = {
        "mode": "dedicated_learning",
        "kiosk_mode_enabled": True,
        "display_school_name": True,
        "school_name": "Example Secondary School",
        "support_message": "Contact the ICT office",
    }
    mutation(value)

    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


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
