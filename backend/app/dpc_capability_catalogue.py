"""Authoritative DPC v3 capability catalogue (Android API 29--35 only)."""

from __future__ import annotations

from typing import TypedDict

CATALOGUE_VERSION = "2026-09-26"
_CONTROL_CAPABILITIES: dict[str, set[str]] = {
    "app_suspension": {"modes.blocked_packages"},
    "application_restrictions": {"application_controls"},
    "device_restrictions": {"device_restrictions"},
    "screen_lock": {"screen_lock"},
    "network_settings": {"network_settings"},
    "wifi_state_control": {"network_settings.allow_wifi"},
    "lock_task": {"modes.lock_task_packages"},
    "screen_time": {"screen_time"},
    "web_filter": {"web_filter"},
    "wifi_only": {"network_controls.wifi_only"},
    "mobile_network_restriction": {
        "network_controls.disallow_mobile_network_configuration"
    },
    "tethering_restriction": {"network_controls.disallow_tethering"},
    "user_vpn_restriction": {"network_controls.disallow_user_vpn"},
    "always_on_filtering_vpn": {"network_controls.always_on_filtering_vpn"},
    "vpn_lockdown": {"network_controls.vpn_lockdown_required"},
    "outgoing_call_restriction": {"telephony_controls.disallow_outgoing_calls"},
    "sms_restriction": {"telephony_controls.disallow_sms"},
    "emergency_call_preservation": {"telephony_controls.preserve_emergency_calls"},
    "forensic_audit_chain": {"audit"},
    "offline_policy_enforcement": {"sync"},
}


class CapabilityRecord(TypedDict):
    capability_id: str
    minimum_dpc_version: int
    android_api_min: int
    android_api_max: int
    controls: list[str]
    evidence_requirement: str
    status: str


CAPABILITIES: dict[str, CapabilityRecord] = {
    key: {
        "capability_id": key,
        "minimum_dpc_version": 1,
        "android_api_min": 33 if key == "wifi_state_control" else 29,
        "android_api_max": 35,
        "controls": sorted(value),
        "evidence_requirement": "authenticated_capability_report",
        "status": "active",
    }
    for key, value in _CONTROL_CAPABILITIES.items()
}


def validate_capabilities(values: list[str], *, api_level: int) -> list[str]:
    if not 29 <= api_level <= 35 or any(
        value not in CAPABILITIES
        or CAPABILITIES[value]["status"] != "active"
        or api_level < CAPABILITIES[value]["android_api_min"]
        for value in values
    ):
        raise ValueError("unknown or unsupported DPC capability")
    return sorted(values)
