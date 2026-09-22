from copy import deepcopy
from uuid import uuid4

import pytest

from app.device_status_contract import (
    DeviceStatusContractError,
    validate_check_in,
    validate_policy_acknowledgement,
)


def check_in() -> dict[str, object]:
    return {
        "protocol_version": 2,
        "check_in_uuid": str(uuid4()),
        "observed_at": "2026-09-20T12:00:00Z",
        "elapsed_realtime_ms": 1000,
        "boot_count": 1,
        "dpc_version": 1,
        "android_version": "10",
        "api_level": 29,
        "security_patch": "2026-09-01",
        "capabilities": ["package_suspension", "lock_task"],
        "current_policy_uuid": None,
        "current_revision_uuid": None,
        "policy_status": "none",
        "enforcement_healthy": True,
        "queued_event_count": 2,
    }


def acknowledgement() -> dict[str, object]:
    return {
        "protocol_version": 2,
        "acknowledgement_uuid": str(uuid4()),
        "observed_at": "2026-09-20T12:00:00Z",
        "elapsed_realtime_ms": 1000,
        "boot_count": 1,
        "policy_uuid": str(uuid4()),
        "revision_uuid": str(uuid4()),
        "outcome": "applied",
        "error_code": None,
    }


def test_check_in_normalizes_capabilities() -> None:
    assert validate_check_in(check_in())["capabilities"] == [
        "lock_task",
        "package_suspension",
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("protocol_version", 1),
        ("api_level", 28),
        ("security_patch", "September 2026"),
        ("policy_status", "expired"),
        ("enforcement_healthy", "yes"),
        ("queued_event_count", -1),
    ],
)
def test_check_in_rejects_invalid_values(field: str, value: object) -> None:
    payload = check_in()
    payload[field] = value
    with pytest.raises(DeviceStatusContractError):
        validate_check_in(payload)


def test_check_in_requires_paired_policy_identity() -> None:
    payload = check_in()
    payload["current_policy_uuid"] = str(uuid4())
    with pytest.raises(DeviceStatusContractError, match="paired"):
        validate_check_in(payload)


def test_acknowledgement_failure_requires_error_code() -> None:
    payload = acknowledgement()
    payload["outcome"] = "failed"
    with pytest.raises(DeviceStatusContractError, match="requires"):
        validate_policy_acknowledgement(payload)
    payload["error_code"] = "package_manager_failure"
    assert (
        validate_policy_acknowledgement(payload)["error_code"]
        == "package_manager_failure"
    )


def test_acknowledgement_clear_requires_empty_policy_identity() -> None:
    payload = acknowledgement()
    payload["outcome"] = "cleared"
    with pytest.raises(DeviceStatusContractError, match="disagree"):
        validate_policy_acknowledgement(payload)
    payload["policy_uuid"] = None
    payload["revision_uuid"] = None
    assert validate_policy_acknowledgement(payload)["outcome"] == "cleared"


def test_contract_rejects_extra_fields() -> None:
    payload = deepcopy(check_in())
    payload["location"] = "excluded"
    with pytest.raises(DeviceStatusContractError):
        validate_check_in(payload)
