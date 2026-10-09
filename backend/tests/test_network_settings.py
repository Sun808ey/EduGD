import json

import pytest
from test_policy_contract_v3 import policy

from app.dpc_capability_catalogue import validate_capabilities
from app.policy_contract import PolicyContractError
from app.policy_contract_v3 import validate_policy_v3


def network_policy():
    value = policy()
    value["network_controls"].update(
        wifi_only=False,
        disallow_mobile_network_configuration=False,
    )
    value["network_settings"] = {
        "allow_wifi": True,
        "allow_mobile_data": True,
        "allow_bluetooth": False,
        "allow_hotspot_creation": False,
        "allow_vpn_changes": False,
        "allow_network_reset": False,
    }
    return value


def test_network_settings_survive_canonical_roundtrip():
    value = validate_policy_v3(network_policy())
    assert value["network_settings"] == network_policy()["network_settings"]
    assert "network_settings" in value["required_capabilities"]
    assert validate_policy_v3(json.loads(json.dumps(value, sort_keys=True))) == value


@pytest.mark.parametrize(
    "change",
    [
        {"allow_wifi": "false"},
        {"allow_bluetooth": 0},
        {"allow_mobile_data": False},
        {"unexpected": True},
    ],
)
def test_network_settings_reject_invalid_or_unenforceable_input(change):
    value = network_policy()
    value["network_settings"].update(change)
    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


def test_network_settings_reject_missing_field():
    value = network_policy()
    del value["network_settings"]["allow_wifi"]
    with pytest.raises(PolicyContractError):
        validate_policy_v3(value)


@pytest.mark.parametrize(
    "field", ["wifi_only", "disallow_tethering", "disallow_user_vpn"]
)
def test_network_settings_reject_conflicting_legacy_controls(field):
    value = network_policy()
    value["network_controls"][field] = not value["network_controls"][field]
    with pytest.raises(PolicyContractError, match="conflicting network controls"):
        validate_policy_v3(value)


def test_wifi_blocking_requires_android_13_capability():
    value = network_policy()
    value["network_settings"]["allow_wifi"] = False
    assert "wifi_state_control" in validate_policy_v3(value)["required_capabilities"]
    with pytest.raises(ValueError):
        validate_capabilities(["wifi_state_control"], api_level=32)
    assert validate_capabilities(["wifi_state_control"], api_level=33) == [
        "wifi_state_control"
    ]


def test_legacy_payload_is_not_upgraded_implicitly():
    assert "network_settings" not in validate_policy_v3(policy())
