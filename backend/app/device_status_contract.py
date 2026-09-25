from __future__ import annotations

import re
from datetime import date, datetime
from uuid import UUID

from app.protocol_versions import CONTROL_STATE_PROTOCOL_VERSION

MAX_CAPABILITIES = 64
MAX_DPC_VERSION = 2_147_483_647
MAX_QUEUED_EVENTS = 1_000_000
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
CHECK_IN_STATUSES = frozenset({"none", "verified", "applied", "stale", "recovery"})
ACK_OUTCOMES = frozenset(
    {"verified", "applied", "failed", "rejected", "rolled_back", "cleared"}
)
_CHECK_IN_KEYS = frozenset(
    {
        "protocol_version",
        "check_in_uuid",
        "observed_at",
        "elapsed_realtime_ms",
        "boot_count",
        "dpc_version",
        "android_version",
        "api_level",
        "security_patch",
        "capabilities",
        "current_policy_uuid",
        "current_revision_uuid",
        "policy_status",
        "enforcement_healthy",
        "queued_event_count",
    }
)
_ACK_KEYS = frozenset(
    {
        "protocol_version",
        "acknowledgement_uuid",
        "observed_at",
        "elapsed_realtime_ms",
        "boot_count",
        "policy_uuid",
        "revision_uuid",
        "outcome",
        "error_code",
    }
)


class DeviceStatusContractError(ValueError):
    pass


def _strict(value: object, keys: frozenset[str], field: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise DeviceStatusContractError(f"invalid {field}")
    return value


def _uuid(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise DeviceStatusContractError(f"invalid {field}")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise DeviceStatusContractError(f"invalid {field}") from error
    if parsed.version != 4 or str(parsed) != value:
        raise DeviceStatusContractError(f"invalid {field}")
    return value


def _optional_uuid(value: object, field: str) -> str | None:
    return None if value is None else _uuid(value, field)


def _integer(value: object, field: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise DeviceStatusContractError(f"invalid {field}")
    return value


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DeviceStatusContractError("invalid observed_at")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise DeviceStatusContractError("invalid observed_at") from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise DeviceStatusContractError("invalid observed_at")
    return value


def _policy_identity(policy: object, revision: object) -> tuple[str | None, str | None]:
    policy_uuid = _optional_uuid(policy, "policy_uuid")
    revision_uuid = _optional_uuid(revision, "revision_uuid")
    if (policy_uuid is None) != (revision_uuid is None):
        raise DeviceStatusContractError("policy and revision identity must be paired")
    return policy_uuid, revision_uuid


def validate_check_in(value: object) -> dict[str, object]:
    payload = _strict(value, _CHECK_IN_KEYS, "device check-in")
    if payload["protocol_version"] != CONTROL_STATE_PROTOCOL_VERSION:
        raise DeviceStatusContractError("unsupported protocol version")
    android_version = payload["android_version"]
    if (
        not isinstance(android_version, str)
        or not 1 <= len(android_version) <= 32
        or not android_version.isprintable()
    ):
        raise DeviceStatusContractError("invalid android_version")
    patch = payload["security_patch"]
    if not isinstance(patch, str):
        raise DeviceStatusContractError("invalid security_patch")
    try:
        if date.fromisoformat(patch).isoformat() != patch:
            raise ValueError
    except ValueError as error:
        raise DeviceStatusContractError("invalid security_patch") from error
    raw_capabilities = payload["capabilities"]
    if (
        not isinstance(raw_capabilities, list)
        or len(raw_capabilities) > MAX_CAPABILITIES
    ):
        raise DeviceStatusContractError("invalid capabilities")
    capabilities: list[str] = []
    for capability in raw_capabilities:
        if not isinstance(capability, str) or _IDENTIFIER.fullmatch(capability) is None:
            raise DeviceStatusContractError("invalid capabilities")
        capabilities.append(capability)
    if len(capabilities) != len(set(capabilities)):
        raise DeviceStatusContractError("duplicate capabilities")
    policy_uuid, revision_uuid = _policy_identity(
        payload["current_policy_uuid"], payload["current_revision_uuid"]
    )
    status = payload["policy_status"]
    if status not in CHECK_IN_STATUSES:
        raise DeviceStatusContractError("invalid policy_status")
    if (status == "none") != (policy_uuid is None):
        raise DeviceStatusContractError("policy status and identity disagree")
    healthy = payload["enforcement_healthy"]
    if not isinstance(healthy, bool):
        raise DeviceStatusContractError("invalid enforcement_healthy")
    return {
        "protocol_version": CONTROL_STATE_PROTOCOL_VERSION,
        "check_in_uuid": _uuid(payload["check_in_uuid"], "check_in_uuid"),
        "observed_at": _timestamp(payload["observed_at"]),
        "elapsed_realtime_ms": _integer(
            payload["elapsed_realtime_ms"], "elapsed_realtime_ms", 0, 2**63 - 1
        ),
        "boot_count": _integer(payload["boot_count"], "boot_count", 0, 2**31 - 1),
        "dpc_version": _integer(
            payload["dpc_version"], "dpc_version", 1, MAX_DPC_VERSION
        ),
        "android_version": android_version,
        "api_level": _integer(payload["api_level"], "api_level", 29, 35),
        "security_patch": patch,
        "capabilities": sorted(capabilities),
        "current_policy_uuid": policy_uuid,
        "current_revision_uuid": revision_uuid,
        "policy_status": status,
        "enforcement_healthy": healthy,
        "queued_event_count": _integer(
            payload["queued_event_count"], "queued_event_count", 0, MAX_QUEUED_EVENTS
        ),
    }


def validate_policy_acknowledgement(value: object) -> dict[str, object]:
    payload = _strict(value, _ACK_KEYS, "policy acknowledgement")
    if payload["protocol_version"] != CONTROL_STATE_PROTOCOL_VERSION:
        raise DeviceStatusContractError("unsupported protocol version")
    policy_uuid, revision_uuid = _policy_identity(
        payload["policy_uuid"], payload["revision_uuid"]
    )
    outcome = payload["outcome"]
    if outcome not in ACK_OUTCOMES:
        raise DeviceStatusContractError("invalid acknowledgement outcome")
    if (outcome == "cleared") != (policy_uuid is None):
        raise DeviceStatusContractError("acknowledgement outcome and identity disagree")
    error_code = payload["error_code"]
    if error_code is not None and (
        not isinstance(error_code, str) or _IDENTIFIER.fullmatch(error_code) is None
    ):
        raise DeviceStatusContractError("invalid error_code")
    if outcome in {"failed", "rejected"} and error_code is None:
        raise DeviceStatusContractError("failed acknowledgement requires error_code")
    if outcome not in {"failed", "rejected"} and error_code is not None:
        raise DeviceStatusContractError(
            "successful acknowledgement cannot include error_code"
        )
    return {
        "protocol_version": CONTROL_STATE_PROTOCOL_VERSION,
        "acknowledgement_uuid": _uuid(
            payload["acknowledgement_uuid"], "acknowledgement_uuid"
        ),
        "observed_at": _timestamp(payload["observed_at"]),
        "elapsed_realtime_ms": _integer(
            payload["elapsed_realtime_ms"], "elapsed_realtime_ms", 0, 2**63 - 1
        ),
        "boot_count": _integer(payload["boot_count"], "boot_count", 0, 2**31 - 1),
        "policy_uuid": policy_uuid,
        "revision_uuid": revision_uuid,
        "outcome": outcome,
        "error_code": error_code,
    }


__all__ = [
    "ACK_OUTCOMES",
    "CHECK_IN_STATUSES",
    "DeviceStatusContractError",
    "validate_check_in",
    "validate_policy_acknowledgement",
]
