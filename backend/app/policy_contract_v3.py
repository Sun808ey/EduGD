"""The signed, privacy-preserving policy contract for DPC protocol v3."""

from __future__ import annotations

import base64
import hashlib
import re
from copy import deepcopy
from typing import cast
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.policy_contract import _PACKAGE, PolicyContractError, canonical_json_bytes
from app.protocol_versions import POLICY_PROTOCOL_VERSION, POLICY_SCHEMA_VERSION

_DOMAIN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_RULE_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_POLICY_CODE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_DEVICE_USE_MODES = frozenset({"normal_managed", "dedicated_learning", "examination"})
_DEVICE_USE_KEYS = frozenset(
    {
        "mode",
        "kiosk_mode_enabled",
        "display_school_name",
        "school_name",
        "support_message",
    }
)
_APPLICATION_TYPES = frozenset(
    {
        "learning_application",
        "digital_textbook",
        "pdf_reader",
        "calculator",
        "approved_browser",
        "accessibility_application",
        "other_approved_application",
    }
)
_APPROVED_APPLICATION_KEYS = frozenset(
    {
        "application_uuid",
        "display_name",
        "package_name",
        "application_type",
        "required",
        "allow_in_kiosk",
    }
)
_APPLICATION_CONTROL_KEYS = frozenset(
    {
        "allow_installation_of_other_applications",
        "allow_installation_from_unknown_sources",
        "allow_uninstall_of_approved_applications",
        "allow_disable_of_approved_applications",
        "allow_google_play_store",
        "allow_file_sharing_applications",
    }
)
_MATERIALIZED_APPLICATION_CONTROL_KEYS = _APPLICATION_CONTROL_KEYS | {
    "file_sharing_packages"
}
_DEVICE_RESTRICTION_KEYS = frozenset(
    {
        "block_factory_reset",
        "block_safe_mode",
        "block_developer_options_and_debugging",
        "block_usb_file_transfer",
        "block_account_changes",
        "block_user_switching",
        "block_network_reset",
        "block_wifi_changes",
        "disable_screenshots",
        "disable_screen_recording",
        "disable_camera",
        "disable_microphone",
        "disable_location",
    }
)
_SCREEN_LOCK_KEYS = frozenset(
    {
        "require_screen_lock",
        "automatic_lock_after_minutes",
        "allow_biometric_unlock",
        "allow_learner_change_lock_method",
    }
)
_SCREEN_LOCK_TIMEOUT_MINUTES = frozenset({1, 5, 10, 15, 30, 60})
_NETWORK_SETTING_KEYS = frozenset(
    {
        "allow_wifi",
        "allow_mobile_data",
        "allow_bluetooth",
        "allow_hotspot_creation",
        "allow_vpn_changes",
        "allow_network_reset",
    }
)
_COMPLIANCE_CHECK_KEYS = frozenset(
    {
        "device_enrolled",
        "dpc_active",
        "policy_version_current",
        "approved_learning_application_installed",
        "kiosk_mode_active",
        "unknown_sources_blocked",
        "factory_reset_restriction_active",
        "required_restrictions_applied",
    }
)
_COMPLIANCE_SETTING_KEYS = _COMPLIANCE_CHECK_KEYS | {
    "connection_review_after_days",
}
_OFFLINE_SETTING_KEYS = frozenset(
    {
        "enforce_last_valid_policy_offline",
        "store_local_policy_copy",
        "queue_events_while_offline",
        "apply_policy_changes_after_reconnection",
        "expire_policy_when_offline",
    }
)
_ADMINISTRATOR_NOTES_MAX_LENGTH = 2000
_DATA_COLLECTION_SETTING_KEYS = frozenset(
    {
        "store_device_asset_number",
        "store_device_policy_version",
        "store_last_synchronisation_time",
        "store_compliance_result",
        "store_administrative_actions",
        "collect_learner_location",
        "read_private_messages",
        "read_photographs",
        "record_microphone",
        "store_browsing_history",
    }
)


def normalize_domain(value: object) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or "/" in value
        or ":" in value
    ):
        raise PolicyContractError("invalid web-filter domain")
    try:
        domain = value.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise PolicyContractError("invalid web-filter domain") from error
    if not _DOMAIN.fullmatch(domain):
        raise PolicyContractError("invalid web-filter domain")
    return domain


def validate_policy_v3(value: object) -> dict[str, object]:
    """Validate a v3 policy without accepting URLs or browsing-history fields."""
    base_keys = {
        "schema_version",
        "timezone",
        "refresh_after_seconds",
        "default_mode",
        "emergency_packages",
        "required_capabilities",
        "minimum_dpc_version",
        "modes",
        "schedules",
        "screen_time",
        "web_filter",
        "network_controls",
        "telephony_controls",
    }
    optional_sections = {
        "device_use",
        "approved_applications",
        "application_controls",
        "device_restrictions",
        "screen_lock",
        "network_settings",
        "compliance_settings",
        "offline_settings",
        "administrator_notes",
        "data_collection_settings",
        "policy_code",
        "description",
    }
    if (
        not isinstance(value, dict)
        or not base_keys.issubset(value)
        or not set(value).issubset(base_keys | optional_sections)
    ):
        raise PolicyContractError("invalid v3 policy")
    # Reuse the fully hardened v2 validation for the common policy body.
    from app.policy_contract import validate_policy_v2

    common = validate_policy_v2(
        {
            key: value[key]
            for key in (
                "schema_version",
                "timezone",
                "refresh_after_seconds",
                "default_mode",
                "emergency_packages",
                "required_capabilities",
                "minimum_dpc_version",
                "modes",
                "schedules",
            )
        }
        | {"schema_version": 2}
    )
    # v2 already validates recurring weekday/minute windows, including
    # duplicate priorities and ambiguous overlaps. Reuse that canonical
    # representation for v3 so the DPC can enforce school timetables.
    screen = value["screen_time"]
    if not isinstance(screen, dict) or set(screen) != {
        "daily_limit_minutes",
        "reset_minute",
        "exhausted_mode_id",
    }:
        raise PolicyContractError("invalid screen_time")
    limit = screen["daily_limit_minutes"]
    reset = screen["reset_minute"]
    exhausted = screen["exhausted_mode_id"]
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1440:
        raise PolicyContractError("invalid daily_limit_minutes")
    if isinstance(reset, bool) or not isinstance(reset, int) or not 0 <= reset <= 1439:
        raise PolicyContractError("invalid reset_minute")
    modes = cast(list[dict[str, object]], common["modes"])
    if not isinstance(exhausted, str) or exhausted not in {m["mode_id"] for m in modes}:
        raise PolicyContractError("invalid exhausted_mode_id")
    web = value["web_filter"]
    if not isinstance(web, dict) or set(web) != {"default_action", "rules"}:
        raise PolicyContractError("invalid web_filter")
    default_action = web["default_action"]
    if default_action not in {"allow", "block"}:
        raise PolicyContractError("invalid web-filter default_action")
    if not isinstance(web["rules"], list) or len(web["rules"]) > 256:
        raise PolicyContractError("invalid web-filter rules")
    rules: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    ids: set[str] = set()
    for raw in web["rules"]:
        if not isinstance(raw, dict) or set(raw) != {
            "rule_id",
            "domain",
            "include_subdomains",
            "action",
            "reason",
        }:
            raise PolicyContractError("invalid web-filter rule")
        rule_id = raw["rule_id"]
        domain = raw["domain"]
        include_subdomains = raw["include_subdomains"]
        action = raw["action"]
        reason = raw["reason"]
        if (
            not isinstance(rule_id, str)
            or not _RULE_ID.fullmatch(rule_id)
            or rule_id in ids
            or not isinstance(include_subdomains, bool)
        ):
            raise PolicyContractError("invalid web-filter rule_id")
        domain = normalize_domain(domain)
        if (
            action not in {"allow", "block"}
            or not isinstance(reason, str)
            or not 1 <= len(reason) <= 256
            or not reason.isprintable()
        ):
            raise PolicyContractError("invalid web-filter rule")
        if (domain, action) in seen:
            raise PolicyContractError("duplicate web-filter rule")
        seen.add((domain, action))
        ids.add(rule_id)
        rules.append(
            {
                "rule_id": rule_id,
                "domain": domain,
                "include_subdomains": include_subdomains,
                "action": action,
                "reason": reason,
            }
        )
    result: dict[str, object] = {
        **common,
        "schema_version": POLICY_SCHEMA_VERSION,
        "screen_time": {
            "daily_limit_minutes": limit,
            "reset_minute": reset,
            "exhausted_mode_id": exhausted,
        },
        "web_filter": {
            "default_action": default_action,
            "rules": sorted(rules, key=lambda r: r["rule_id"]),
        },
        "network_controls": _validate_network_controls(value["network_controls"]),
        "telephony_controls": _validate_telephony_controls(value["telephony_controls"]),
    }
    if "device_use" in value:
        result["device_use"] = _validate_device_use(value["device_use"])
    if "approved_applications" in value:
        result["approved_applications"] = _validate_approved_applications(
            value["approved_applications"]
        )
    if "application_controls" in value:
        result["application_controls"] = _validate_application_controls(
            value["application_controls"]
        )
    if "device_restrictions" in value:
        result["device_restrictions"] = _validate_device_restrictions(
            value["device_restrictions"]
        )
    if "screen_lock" in value:
        result["screen_lock"] = _validate_screen_lock(value["screen_lock"])
    if "network_settings" in value:
        network = value["network_settings"]
        if not isinstance(network, dict) or set(network) != _NETWORK_SETTING_KEYS:
            raise PolicyContractError("invalid network_settings")
        if any(not isinstance(item, bool) for item in network.values()):
            raise PolicyContractError("network settings must be boolean")
        if not network["allow_mobile_data"]:
            raise PolicyContractError(
                "mobile-data blocking requires unavailable carrier or system privileges"
            )
        controls = cast(dict[str, bool], result["network_controls"])
        if (
            controls["wifi_only"]
            or controls["disallow_mobile_network_configuration"]
            or controls["disallow_tethering"] == network["allow_hotspot_creation"]
            or controls["disallow_user_vpn"] == network["allow_vpn_changes"]
        ):
            raise PolicyContractError("conflicting network controls")
        restrictions = cast(dict[str, bool] | None, result.get("device_restrictions"))
        if (
            restrictions
            and restrictions["block_network_reset"] == network["allow_network_reset"]
        ):
            raise PolicyContractError("conflicting network reset settings")
        result["network_settings"] = {key: network[key] for key in sorted(network)}
        capabilities = set(cast(list[str], result["required_capabilities"])) | {
            "network_settings"
        }
        if not network["allow_wifi"]:
            capabilities.add("wifi_state_control")
        result["required_capabilities"] = sorted(capabilities)
    if "compliance_settings" in value:
        result["compliance_settings"] = _validate_compliance_settings(
            value["compliance_settings"]
        )
    if "offline_settings" in value:
        result["offline_settings"] = _validate_offline_settings(
            value["offline_settings"]
        )
    if "administrator_notes" in value:
        result["administrator_notes"] = _validate_administrator_notes(
            value["administrator_notes"]
        )
    if "data_collection_settings" in value:
        result["data_collection_settings"] = _validate_data_collection_settings(
            value["data_collection_settings"]
        )
    if "policy_code" in value or "description" in value:
        if "policy_code" not in value or "description" not in value:
            raise PolicyContractError(
                "policy code and description must be provided together"
            )
        result["policy_code"], result["description"] = _validate_policy_identity(
            value["policy_code"], value["description"]
        )
    device_use = result.get("device_use")
    if isinstance(device_use, dict) and device_use["kiosk_mode_enabled"]:
        applications = result.get("approved_applications")
        if not isinstance(applications, list) or not any(
            isinstance(application, dict) and application["allow_in_kiosk"]
            for application in applications
        ):
            raise PolicyContractError(
                "kiosk mode requires an approved kiosk application"
            )
    if isinstance(device_use, dict) and device_use["mode"] == "examination":
        examination_restrictions = result.get("device_restrictions")
        if (
            not isinstance(examination_restrictions, dict)
            or not examination_restrictions["disable_camera"]
            or not examination_restrictions["disable_screenshots"]
            or not examination_restrictions["disable_microphone"]
        ):
            raise PolicyContractError(
                "examination mode requires camera, screenshots, and microphone disabled"
            )
    network = result.get("network_settings")
    wifi_restrictions = result.get("device_restrictions")
    if (
        isinstance(network, dict)
        and isinstance(wifi_restrictions, dict)
        and wifi_restrictions["block_wifi_changes"]
        and not network["allow_wifi"]
    ):
        raise PolicyContractError(
            "Wi-Fi changes cannot be blocked when Wi-Fi is disabled"
        )
    if "approved_applications" in result and "device_use" in result:
        emergency_packages = result.get("emergency_packages")
        if (
            not isinstance(emergency_packages, list)
            or "io.github.sun808ey.edugd.dpc" not in emergency_packages
        ):
            raise PolicyContractError(
                "the EDUGD DPC package must remain an emergency package"
            )
    return result


def _validate_device_use(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _DEVICE_USE_KEYS:
        raise PolicyContractError("invalid device_use")
    mode = value["mode"]
    if not isinstance(mode, str) or mode not in _DEVICE_USE_MODES:
        raise PolicyContractError("invalid device_use mode")
    if not isinstance(value["kiosk_mode_enabled"], bool):
        raise PolicyContractError("device_use kiosk mode must be boolean")
    if not isinstance(value["display_school_name"], bool):
        raise PolicyContractError("device_use school-name display must be boolean")
    support_message = value["support_message"]
    if (
        not isinstance(support_message, str)
        or not 1 <= len(support_message.strip()) <= 256
        or not support_message.isprintable()
    ):
        raise PolicyContractError("invalid device_use support message")
    school_name = value["school_name"]
    if school_name is not None and (
        not isinstance(school_name, str)
        or not 1 <= len(school_name.strip()) <= 160
        or not school_name.isprintable()
    ):
        raise PolicyContractError("invalid device_use school name")
    if not value["display_school_name"] and school_name is not None:
        raise PolicyContractError("school name must be hidden when display is disabled")
    return {
        "mode": mode,
        "kiosk_mode_enabled": value["kiosk_mode_enabled"],
        "display_school_name": value["display_school_name"],
        "school_name": school_name.strip() if isinstance(school_name, str) else None,
        "support_message": support_message.strip(),
    }


def _validate_approved_applications(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 256:
        raise PolicyContractError("approved_applications must not be empty")
    applications: list[dict[str, object]] = []
    seen_uuids: set[str] = set()
    seen_packages: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict) or set(raw) != _APPROVED_APPLICATION_KEYS:
            raise PolicyContractError("invalid approved application")
        application_uuid = raw["application_uuid"]
        try:
            parsed_uuid = UUID(str(application_uuid))
        except (AttributeError, ValueError):
            raise PolicyContractError("invalid approved application UUID") from None
        if parsed_uuid.version != 4 or str(parsed_uuid) != application_uuid:
            raise PolicyContractError("invalid approved application UUID")
        if application_uuid in seen_uuids:
            raise PolicyContractError("duplicate approved application")
        seen_uuids.add(application_uuid)
        display_name = raw["display_name"]
        package_name = raw["package_name"]
        if (
            not isinstance(display_name, str)
            or not 1 <= len(display_name.strip()) <= 120
            or not display_name.isprintable()
            or not isinstance(package_name, str)
            or _PACKAGE.fullmatch(package_name) is None
            or package_name in seen_packages
        ):
            raise PolicyContractError("invalid approved application identity")
        seen_packages.add(package_name)
        application_type = raw["application_type"]
        if (
            not isinstance(application_type, str)
            or application_type not in _APPLICATION_TYPES
        ):
            raise PolicyContractError("invalid approved application type")
        if not isinstance(raw["required"], bool) or not isinstance(
            raw["allow_in_kiosk"], bool
        ):
            raise PolicyContractError("invalid approved application flags")
        applications.append(
            {
                "application_uuid": application_uuid,
                "display_name": display_name.strip(),
                "package_name": package_name,
                "application_type": application_type,
                "required": raw["required"],
                "allow_in_kiosk": raw["allow_in_kiosk"],
            }
        )
    return sorted(applications, key=lambda item: str(item["package_name"]))


def _validate_application_controls(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) not in {
        _APPLICATION_CONTROL_KEYS,
        _MATERIALIZED_APPLICATION_CONTROL_KEYS,
    }:
        raise PolicyContractError("invalid application_controls")
    if any(not isinstance(value[key], bool) for key in _APPLICATION_CONTROL_KEYS):
        raise PolicyContractError("application controls must be boolean")
    file_sharing_packages = value.get("file_sharing_packages", [])
    if (
        not isinstance(file_sharing_packages, list)
        or len(file_sharing_packages) > 256
        or any(
            not isinstance(package_name, str)
            or _PACKAGE.fullmatch(package_name) is None
            for package_name in file_sharing_packages
        )
        or len(file_sharing_packages) != len(set(file_sharing_packages))
    ):
        raise PolicyContractError("invalid file-sharing package list")
    return {
        **{key: value[key] for key in sorted(_APPLICATION_CONTROL_KEYS)},
        "file_sharing_packages": sorted(file_sharing_packages),
    }


def _validate_device_restrictions(value: object) -> dict[str, bool]:
    if not isinstance(value, dict) or set(value) != _DEVICE_RESTRICTION_KEYS:
        raise PolicyContractError("invalid device_restrictions")
    if any(not isinstance(value[key], bool) for key in _DEVICE_RESTRICTION_KEYS):
        raise PolicyContractError("device restrictions must be boolean")
    return {key: value[key] for key in sorted(_DEVICE_RESTRICTION_KEYS)}


def _validate_screen_lock(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _SCREEN_LOCK_KEYS:
        raise PolicyContractError("invalid screen_lock")
    if not isinstance(value["require_screen_lock"], bool):
        raise PolicyContractError("screen-lock requirement must be boolean")
    timeout = value["automatic_lock_after_minutes"]
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or timeout not in _SCREEN_LOCK_TIMEOUT_MINUTES
    ):
        raise PolicyContractError("invalid automatic lock timeout")
    if not isinstance(value["allow_biometric_unlock"], bool):
        raise PolicyContractError("biometric unlock choice must be boolean")
    if not isinstance(value["allow_learner_change_lock_method"], bool):
        raise PolicyContractError("lock-method change choice must be boolean")
    return {key: value[key] for key in sorted(_SCREEN_LOCK_KEYS)}


def _validate_compliance_settings(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _COMPLIANCE_SETTING_KEYS:
        raise PolicyContractError("invalid compliance_settings")
    if any(not isinstance(value[key], bool) for key in _COMPLIANCE_CHECK_KEYS):
        raise PolicyContractError("compliance checks must be boolean")
    threshold = value["connection_review_after_days"]
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, int)
        or not 1 <= threshold <= 30
    ):
        raise PolicyContractError("invalid connection review threshold")
    return {key: value[key] for key in sorted(_COMPLIANCE_CHECK_KEYS)} | {
        "connection_review_after_days": threshold
    }


def _validate_offline_settings(value: object) -> dict[str, bool]:
    if not isinstance(value, dict) or set(value) != _OFFLINE_SETTING_KEYS:
        raise PolicyContractError("invalid offline_settings")
    if any(not isinstance(value[key], bool) for key in _OFFLINE_SETTING_KEYS):
        raise PolicyContractError("offline settings must be boolean")
    required_true = _OFFLINE_SETTING_KEYS - {"expire_policy_when_offline"}
    if (
        any(not value[key] for key in required_true)
        or value["expire_policy_when_offline"]
    ):
        raise PolicyContractError("offline policy expiry is not permitted")
    return {key: value[key] for key in sorted(_OFFLINE_SETTING_KEYS)}


def _validate_administrator_notes(value: object) -> str:
    if not isinstance(value, str):
        raise PolicyContractError("administrator notes must be text")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized or len(normalized) > _ADMINISTRATOR_NOTES_MAX_LENGTH:
        raise PolicyContractError("invalid administrator notes")
    if any(
        not character.isprintable() and character not in "\n\t"
        for character in normalized
    ):
        raise PolicyContractError("administrator notes contain unsupported characters")
    return normalized


def _validate_data_collection_settings(value: object) -> dict[str, bool]:
    if not isinstance(value, dict) or set(value) != _DATA_COLLECTION_SETTING_KEYS:
        raise PolicyContractError("invalid data_collection_settings")
    if any(not isinstance(value[key], bool) for key in _DATA_COLLECTION_SETTING_KEYS):
        raise PolicyContractError("data collection settings must be boolean")
    management_fields = {
        "store_device_asset_number",
        "store_device_policy_version",
        "store_last_synchronisation_time",
        "store_compliance_result",
        "store_administrative_actions",
    }
    if any(not value[key] for key in management_fields):
        raise PolicyContractError(
            "required device-management collection cannot be disabled"
        )
    surveillance_fields = _DATA_COLLECTION_SETTING_KEYS - management_fields
    if any(value[key] for key in surveillance_fields):
        raise PolicyContractError("learner-content collection is not permitted")
    return {key: value[key] for key in sorted(_DATA_COLLECTION_SETTING_KEYS)}


def _validate_policy_identity(code: object, description: object) -> tuple[str, str]:
    if not isinstance(code, str) or not _POLICY_CODE.fullmatch(code):
        raise PolicyContractError("invalid policy code")
    if (
        not isinstance(description, str)
        or not 1 <= len(description.strip()) <= 2048
        or not description.strip().isprintable()
    ):
        raise PolicyContractError("invalid policy description")
    return code, description.strip()


def _validate_network_controls(value: object) -> dict[str, bool]:
    keys = {
        "wifi_only",
        "disallow_mobile_network_configuration",
        "disallow_tethering",
        "disallow_user_vpn",
        "always_on_filtering_vpn",
        "vpn_lockdown_required",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise PolicyContractError("invalid network_controls")
    if any(not isinstance(item, bool) for item in value.values()):
        raise PolicyContractError("network_controls must be boolean")
    if value["vpn_lockdown_required"] and not value["always_on_filtering_vpn"]:
        raise PolicyContractError(
            "vpn_lockdown_required requires always_on_filtering_vpn"
        )
    return {key: value[key] for key in sorted(keys)}


def _validate_telephony_controls(value: object) -> dict[str, bool]:
    keys = {"disallow_outgoing_calls", "disallow_sms", "preserve_emergency_calls"}
    if not isinstance(value, dict) or set(value) != keys:
        raise PolicyContractError("invalid telephony_controls")
    if any(not isinstance(item, bool) for item in value.values()):
        raise PolicyContractError("telephony_controls must be boolean")
    if value["preserve_emergency_calls"] is not True:
        raise PolicyContractError("emergency calling must remain enabled")
    return {key: value[key] for key in sorted(keys)}


def policy_v3_hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(validate_policy_v3(value))).hexdigest()


def build_policy_v3_envelope(
    *,
    policy_uuid: str,
    revision_uuid: str,
    revision_number: int,
    issued_at: str,
    signing_key_id: str,
    payload: object,
) -> dict[str, object]:
    """Build the exact unsigned object a v3 DPC verifies before activation."""
    from app.policy_contract import build_policy_envelope

    # Reuse UUID, timestamp and key-id canonical checks, then replace the v2 payload.
    checked = validate_policy_v3(payload)
    v2_payload = {
        "schema_version": 2,
        "timezone": checked["timezone"],
        "refresh_after_seconds": checked["refresh_after_seconds"],
        "default_mode": checked["default_mode"],
        "emergency_packages": checked["emergency_packages"],
        "required_capabilities": checked["required_capabilities"],
        "minimum_dpc_version": checked["minimum_dpc_version"],
        "modes": checked["modes"],
        "schedules": checked["schedules"],
    }
    base = build_policy_envelope(
        policy_uuid=policy_uuid,
        revision_uuid=revision_uuid,
        revision_number=revision_number,
        issued_at=issued_at,
        signing_key_id=signing_key_id,
        payload=v2_payload,
    )
    return {
        **base,
        "protocol_version": POLICY_PROTOCOL_VERSION,
        "payload_hash": policy_v3_hash(checked),
        "payload": checked,
    }


def sign_policy_v3_envelope(
    envelope: dict[str, object], private_key: Ed25519PrivateKey
) -> dict[str, object]:
    signature = private_key.sign(canonical_json_bytes(envelope))
    return {
        **deepcopy(envelope),
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii"),
    }


def verify_policy_v3_envelope(
    envelope: object, public_key: Ed25519PublicKey
) -> dict[str, object]:
    if (
        not isinstance(envelope, dict)
        or set(envelope)
        != {
            "protocol_version",
            "policy_uuid",
            "revision_uuid",
            "revision_number",
            "issued_at",
            "payload_hash",
            "signing_key_id",
            "payload",
            "signature",
        }
        or envelope.get("protocol_version") != POLICY_PROTOCOL_VERSION
    ):
        raise PolicyContractError("invalid v3 policy envelope")
    try:
        signature = base64.urlsafe_b64decode(
            str(envelope["signature"]) + "=" * (-len(str(envelope["signature"])) % 4)
        )
        unsigned = {key: value for key, value in envelope.items() if key != "signature"}
        public_key.verify(signature, canonical_json_bytes(unsigned))
    except (ValueError, InvalidSignature) as error:
        raise PolicyContractError("invalid v3 policy signature") from error
    rebuilt = build_policy_v3_envelope(
        policy_uuid=str(envelope["policy_uuid"]),
        revision_uuid=str(envelope["revision_uuid"]),
        revision_number=envelope["revision_number"],
        issued_at=str(envelope["issued_at"]),
        signing_key_id=str(envelope["signing_key_id"]),
        payload=envelope["payload"],
    )
    if rebuilt != unsigned:
        raise PolicyContractError("invalid v3 policy envelope")
    return rebuilt
