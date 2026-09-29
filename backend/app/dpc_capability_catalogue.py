"""Authoritative DPC v3 capability catalogue (Android API 29--35 only)."""

from __future__ import annotations

CATALOGUE_VERSION = "2026-09-26"
_CONTROL_CAPABILITIES = {
    "app_suspension": {"modes.blocked_packages"}, "lock_task": {"modes.lock_task_packages"},
    "screen_time": {"screen_time"}, "web_filter": {"web_filter"},
    "wifi_only": {"network_controls.wifi_only"},
    "mobile_network_restriction": {"network_controls.disallow_mobile_network_configuration"},
    "tethering_restriction": {"network_controls.disallow_tethering"},
    "user_vpn_restriction": {"network_controls.disallow_user_vpn"},
    "always_on_filtering_vpn": {"network_controls.always_on_filtering_vpn"},
    "vpn_lockdown": {"network_controls.vpn_lockdown_required"},
    "outgoing_call_restriction": {"telephony_controls.disallow_outgoing_calls"},
    "sms_restriction": {"telephony_controls.disallow_sms"},
    "emergency_call_preservation": {"telephony_controls.preserve_emergency_calls"},
    "forensic_audit_chain": {"audit"}, "offline_policy_enforcement": {"sync"},
}
CAPABILITIES = {key: {"capability_id": key, "minimum_dpc_version": 1, "android_api_min": 29, "android_api_max": 35, "controls": sorted(value), "evidence_requirement": "authenticated_capability_report", "status": "active"} for key, value in _CONTROL_CAPABILITIES.items()}

def validate_capabilities(values: list[str], *, api_level: int) -> list[str]:
    if not 29 <= api_level <= 35 or any(value not in CAPABILITIES or CAPABILITIES[value]["status"] != "active" for value in values):
        raise ValueError("unknown or unsupported DPC capability")
    return sorted(values)
