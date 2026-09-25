import pytest

from app.policy_contract import PolicyContractError
from app.policy_contract_v3 import normalize_domain, validate_policy_v3


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
