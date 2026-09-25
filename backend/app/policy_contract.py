from __future__ import annotations

import base64
import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# These names are explicitly legacy. Android-facing v3 contracts use the
# version constants in ``app.protocol_versions`` instead.
LEGACY_POLICY_SCHEMA_VERSION = 2
LEGACY_DPC_PROTOCOL_VERSION = 2
MIN_REFRESH_SECONDS = 300
MAX_REFRESH_SECONDS = 604_800
MAX_MODES = 16
MAX_SCHEDULES = 64
MAX_PACKAGES_PER_LIST = 256
MAX_CAPABILITIES = 64

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PACKAGE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_KEY_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

_DEVICE_CONTROL_KEYS = frozenset(
    {
        "camera_disabled",
        "screen_capture_disabled",
        "unknown_sources_disabled",
        "factory_reset_disabled",
        "safe_boot_disabled",
        "add_users_disabled",
        "account_changes_disabled",
        "usb_file_transfer_disabled",
    }
)
_POLICY_KEYS = frozenset(
    {
        "schema_version",
        "timezone",
        "refresh_after_seconds",
        "default_mode",
        "emergency_packages",
        "required_capabilities",
        "minimum_dpc_version",
        "modes",
        "schedules",
    }
)
_MODE_KEYS = frozenset(
    {
        "mode_id",
        "application_mode",
        "allowed_packages",
        "blocked_packages",
        "lock_task_packages",
        "user_restrictions",
        "device_controls",
    }
)
_SCHEDULE_KEYS = frozenset(
    {"schedule_id", "days", "start_minute", "end_minute", "mode_id", "priority"}
)
_ENVELOPE_KEYS = frozenset(
    {
        "protocol_version",
        "policy_uuid",
        "revision_uuid",
        "revision_number",
        "issued_at",
        "payload_hash",
        "signing_key_id",
        "payload",
    }
)


class PolicyContractError(ValueError):
    pass


def _identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise PolicyContractError(f"invalid {field}")
    return value


def _bounded_int(value: object, field: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise PolicyContractError(f"invalid {field}")
    return value


def _package_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_PACKAGES_PER_LIST:
        raise PolicyContractError(f"invalid {field}")
    packages: list[str] = []
    for item in value:
        if not isinstance(item, str) or _PACKAGE.fullmatch(item) is None:
            raise PolicyContractError(f"invalid {field}")
        packages.append(item)
    if len(packages) != len(set(packages)):
        raise PolicyContractError(f"duplicate {field}")
    return sorted(packages)


def _identifier_list(value: object, field: str, maximum: int) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise PolicyContractError(f"invalid {field}")
    result = [_identifier(item, field) for item in value]
    if len(result) != len(set(result)):
        raise PolicyContractError(f"duplicate {field}")
    return sorted(result)


def _strict_keys(value: object, keys: frozenset[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PolicyContractError(f"invalid {field}")
    return value


def validate_policy_v2(value: object) -> dict[str, object]:
    policy = _strict_keys(value, _POLICY_KEYS, "policy")
    if policy["schema_version"] != LEGACY_POLICY_SCHEMA_VERSION:
        raise PolicyContractError("unsupported policy schema version")
    if policy["timezone"] != "Africa/Kampala":
        raise PolicyContractError("unsupported policy timezone")

    emergency_packages = _package_list(
        policy["emergency_packages"], "emergency_packages"
    )
    if not emergency_packages:
        raise PolicyContractError("emergency_packages must not be empty")
    required_capabilities = _identifier_list(
        policy["required_capabilities"], "required_capabilities", MAX_CAPABILITIES
    )

    raw_modes = policy["modes"]
    if not isinstance(raw_modes, list) or not 1 <= len(raw_modes) <= MAX_MODES:
        raise PolicyContractError("invalid modes")
    modes: list[dict[str, object]] = []
    mode_ids: set[str] = set()
    for raw_mode in raw_modes:
        mode = _strict_keys(raw_mode, _MODE_KEYS, "mode")
        mode_id = _identifier(mode["mode_id"], "mode_id")
        if mode_id in mode_ids:
            raise PolicyContractError("duplicate mode_id")
        mode_ids.add(mode_id)
        if mode["application_mode"] != "allowlist":
            raise PolicyContractError("application_mode must be allowlist")
        allowed = _package_list(mode["allowed_packages"], "allowed_packages")
        blocked = _package_list(mode["blocked_packages"], "blocked_packages")
        lock_task = _package_list(mode["lock_task_packages"], "lock_task_packages")
        if set(allowed) & set(blocked):
            raise PolicyContractError("allowed and blocked packages overlap")
        if not set(emergency_packages).issubset(allowed):
            raise PolicyContractError("every mode must allow emergency packages")
        if not set(lock_task).issubset(allowed):
            raise PolicyContractError("lock task packages must be allowed")
        controls = _strict_keys(
            mode["device_controls"], _DEVICE_CONTROL_KEYS, "device_controls"
        )
        if any(not isinstance(controls[key], bool) for key in _DEVICE_CONTROL_KEYS):
            raise PolicyContractError("device controls must be boolean")
        modes.append(
            {
                "mode_id": mode_id,
                "application_mode": "allowlist",
                "allowed_packages": allowed,
                "blocked_packages": blocked,
                "lock_task_packages": lock_task,
                "user_restrictions": _identifier_list(
                    mode["user_restrictions"], "user_restrictions", MAX_CAPABILITIES
                ),
                "device_controls": {
                    key: controls[key] for key in sorted(_DEVICE_CONTROL_KEYS)
                },
            }
        )

    default_mode = _identifier(policy["default_mode"], "default_mode")
    if default_mode not in mode_ids:
        raise PolicyContractError("default_mode does not exist")

    raw_schedules = policy["schedules"]
    if not isinstance(raw_schedules, list) or len(raw_schedules) > MAX_SCHEDULES:
        raise PolicyContractError("invalid schedules")
    schedules: list[dict[str, object]] = []
    schedule_ids: set[str] = set()
    occupied: set[tuple[int, int, int]] = set()
    for raw_schedule in raw_schedules:
        schedule = _strict_keys(raw_schedule, _SCHEDULE_KEYS, "schedule")
        schedule_id = _identifier(schedule["schedule_id"], "schedule_id")
        if schedule_id in schedule_ids:
            raise PolicyContractError("duplicate schedule_id")
        schedule_ids.add(schedule_id)
        days_value = schedule["days"]
        if not isinstance(days_value, list) or not days_value:
            raise PolicyContractError("invalid schedule days")
        days = sorted({_bounded_int(day, "schedule day", 1, 7) for day in days_value})
        if len(days) != len(days_value):
            raise PolicyContractError("duplicate schedule day")
        start = _bounded_int(schedule["start_minute"], "start_minute", 0, 1439)
        end = _bounded_int(schedule["end_minute"], "end_minute", 0, 1439)
        if start == end:
            raise PolicyContractError("schedule window must not be empty")
        priority = _bounded_int(schedule["priority"], "priority", 0, 1000)
        mode_id = _identifier(schedule["mode_id"], "mode_id")
        if mode_id not in mode_ids:
            raise PolicyContractError("schedule mode does not exist")
        minutes = (
            range(start, end)
            if start < end
            else list(range(start, 1440)) + list(range(0, end))
        )
        for day in days:
            for minute in minutes:
                actual_day = day % 7 + 1 if start > end and minute < end else day
                key = (actual_day, minute, priority)
                if key in occupied:
                    raise PolicyContractError("ambiguous schedules share a priority")
                occupied.add(key)
        schedules.append(
            {
                "schedule_id": schedule_id,
                "days": days,
                "start_minute": start,
                "end_minute": end,
                "mode_id": mode_id,
                "priority": priority,
            }
        )

    return {
        "schema_version": LEGACY_POLICY_SCHEMA_VERSION,
        "timezone": "Africa/Kampala",
        "refresh_after_seconds": _bounded_int(
            policy["refresh_after_seconds"],
            "refresh_after_seconds",
            MIN_REFRESH_SECONDS,
            MAX_REFRESH_SECONDS,
        ),
        "default_mode": default_mode,
        "emergency_packages": emergency_packages,
        "required_capabilities": required_capabilities,
        "minimum_dpc_version": _bounded_int(
            policy["minimum_dpc_version"], "minimum_dpc_version", 1, 2_147_483_647
        ),
        "modes": sorted(modes, key=lambda item: str(item["mode_id"])),
        "schedules": sorted(schedules, key=lambda item: str(item["schedule_id"])),
    }


def canonical_json_bytes(value: object) -> bytes:
    def normalize(item: object) -> object:
        if item is None or isinstance(item, (bool, int)):
            return item
        if isinstance(item, str):
            return unicodedata.normalize("NFC", item)
        if isinstance(item, list):
            return [normalize(child) for child in item]
        if isinstance(item, dict) and all(isinstance(key, str) for key in item):
            return {
                unicodedata.normalize("NFC", key): normalize(child)
                for key, child in item.items()
            }
        raise PolicyContractError("value cannot be canonically encoded")

    return json.dumps(
        normalize(value),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def policy_payload_hash(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(validate_policy_v2(payload))).hexdigest()


def _canonical_uuid(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise PolicyContractError(f"invalid {field}")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise PolicyContractError(f"invalid {field}") from error
    if parsed.version != 4 or str(parsed) != value:
        raise PolicyContractError(f"invalid {field}")
    return value


def _issued_at(value: object) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PolicyContractError("invalid issued_at")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise PolicyContractError("invalid issued_at") from error
    if parsed.tzinfo is None or parsed.astimezone(UTC).microsecond != 0:
        raise PolicyContractError("invalid issued_at")
    canonical = parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if canonical != value:
        raise PolicyContractError("invalid issued_at")
    return value


def build_policy_envelope(
    *,
    policy_uuid: str,
    revision_uuid: str,
    revision_number: int,
    issued_at: str,
    signing_key_id: str,
    payload: object,
) -> dict[str, object]:
    if not isinstance(signing_key_id, str) or _KEY_ID.fullmatch(signing_key_id) is None:
        raise PolicyContractError("invalid signing_key_id")
    canonical_payload = validate_policy_v2(payload)
    return {
        "protocol_version": LEGACY_DPC_PROTOCOL_VERSION,
        "policy_uuid": _canonical_uuid(policy_uuid, "policy_uuid"),
        "revision_uuid": _canonical_uuid(revision_uuid, "revision_uuid"),
        "revision_number": _bounded_int(
            revision_number, "revision_number", 1, 2_147_483_647
        ),
        "issued_at": _issued_at(issued_at),
        "payload_hash": hashlib.sha256(
            canonical_json_bytes(canonical_payload)
        ).hexdigest(),
        "signing_key_id": signing_key_id,
        "payload": canonical_payload,
    }


def _validate_policy_envelope(envelope: object) -> dict[str, object]:
    data = _strict_keys(envelope, _ENVELOPE_KEYS, "policy envelope")
    if data["protocol_version"] != LEGACY_DPC_PROTOCOL_VERSION:
        raise PolicyContractError("unsupported protocol version")
    canonical = build_policy_envelope(
        policy_uuid=data["policy_uuid"],
        revision_uuid=data["revision_uuid"],
        revision_number=data["revision_number"],
        issued_at=data["issued_at"],
        signing_key_id=data["signing_key_id"],
        payload=data["payload"],
    )
    if data["payload_hash"] != canonical["payload_hash"]:
        raise PolicyContractError("policy payload hash mismatch")
    return canonical


def sign_policy_envelope(
    envelope: object, private_key: Ed25519PrivateKey
) -> dict[str, object]:
    canonical = _validate_policy_envelope(envelope)
    signature = private_key.sign(canonical_json_bytes(canonical))
    return {
        **deepcopy(canonical),
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii"),
    }


def verify_policy_envelope(
    signed_envelope: object, public_key: Ed25519PublicKey
) -> dict[str, object]:
    if not isinstance(signed_envelope, dict) or set(
        signed_envelope
    ) != _ENVELOPE_KEYS | {"signature"}:
        raise PolicyContractError("invalid signed policy envelope")
    signature_text = signed_envelope["signature"]
    if not isinstance(signature_text, str):
        raise PolicyContractError("invalid policy signature")
    try:
        signature = base64.urlsafe_b64decode(
            signature_text + "=" * (-len(signature_text) % 4)
        )
    except (ValueError, TypeError) as error:
        raise PolicyContractError("invalid policy signature") from error
    if (
        len(signature) != 64
        or base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
        != signature_text
    ):
        raise PolicyContractError("invalid policy signature")
    unsigned = {key: signed_envelope[key] for key in _ENVELOPE_KEYS}
    canonical = _validate_policy_envelope(unsigned)
    try:
        public_key.verify(signature, canonical_json_bytes(canonical))
    except InvalidSignature as error:
        raise PolicyContractError("invalid policy signature") from error
    return canonical


__all__ = [
    "LEGACY_DPC_PROTOCOL_VERSION",
    "LEGACY_POLICY_SCHEMA_VERSION",
    "PolicyContractError",
    "build_policy_envelope",
    "canonical_json_bytes",
    "policy_payload_hash",
    "sign_policy_envelope",
    "validate_policy_v2",
    "verify_policy_envelope",
]
