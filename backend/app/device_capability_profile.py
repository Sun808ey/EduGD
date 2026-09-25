"""Validate reported handlers and resolve a policy for one verified device model.

Package names and a DPC report alone are not proof of platform signing. A
separate trusted verification step must set ``attested`` for each handler.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.android_integration_config import (
    DISCOVERY_ROLES,
    DPC_APPLICATION_ID,
    INITIAL_EDUCATIONAL_APPS,
    SYSTEM_UI_PACKAGE,
)
from app.physical_certification import verify_certification_record
from app.policy_contract import PolicyContractError, validate_policy_v2

_PACKAGE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")


def _package(value: object) -> str:
    if not isinstance(value, str) or _PACKAGE.fullmatch(value) is None:
        raise PolicyContractError("invalid discovered package")
    return value


def validate_device_capability_profile(
    value: object, *, verified_handlers: set[tuple[str, str]]
) -> dict[str, object]:
    """Reject incomplete, duplicate, or unverified emergency discovery."""
    if not isinstance(value, dict) or set(value) != {
        "model",
        "handlers",
        "system_dependencies",
        "emergency_call_tested",
    }:
        raise PolicyContractError("invalid device capability profile")
    model = value["model"]
    if (
        not isinstance(model, str)
        or not 1 <= len(model) <= 120
        or not model.isprintable()
    ):
        raise PolicyContractError("invalid device model")
    handlers = value["handlers"]
    if not isinstance(handlers, list) or not 4 <= len(handlers) <= 16:
        raise PolicyContractError("invalid discovered handlers")
    roles: set[str] = set()
    packages: set[str] = set()
    checked: list[dict[str, object]] = []
    for handler in handlers:
        if not isinstance(handler, dict) or set(handler) != {
            "role",
            "package",
            "system_signed",
            "attested",
        }:
            raise PolicyContractError("invalid discovered handler")
        role = handler["role"]
        if role not in DISCOVERY_ROLES or role in roles:
            raise PolicyContractError("duplicate or unknown handler role")
        package = _package(handler["package"])
        if handler["system_signed"] is not True or handler["attested"] is not True:
            raise PolicyContractError("emergency handler is not verified")
        if (role, package) not in verified_handlers:
            raise PolicyContractError(
                "emergency handler lacks independent verification"
            )
        roles.add(role)
        packages.add(package)
        checked.append(
            {"role": role, "package": package, "system_signed": True, "attested": True}
        )
    if roles != DISCOVERY_ROLES or value["emergency_call_tested"] is not True:
        raise PolicyContractError("emergency calling is unresolved or untested")
    dependencies = value["system_dependencies"]
    if not isinstance(dependencies, list) or len(dependencies) > 64:
        raise PolicyContractError("invalid system dependencies")
    resolved = [_package(item) for item in dependencies]
    if len(resolved) != len(set(resolved)):
        raise PolicyContractError("duplicate system dependency")
    if SYSTEM_UI_PACKAGE not in resolved:
        raise PolicyContractError("System UI must be preserved")
    return {
        "model": model,
        "handlers": sorted(checked, key=lambda x: str(x["role"])),
        "system_dependencies": sorted(resolved),
        "emergency_call_tested": True,
    }


def resolve_policy_for_device(
    template: object,
    profile: object,
    *,
    installed_packages: set[str],
    verified_handlers: set[tuple[str, str]],
) -> dict[str, object]:
    """Preserve essential packages while rejecting unknown allowlist entries."""
    checked_profile = validate_device_capability_profile(
        profile, verified_handlers=verified_handlers
    )
    if not isinstance(template, dict):
        raise PolicyContractError("invalid policy template")
    data: dict[str, Any] = deepcopy(template)
    handlers = checked_profile["handlers"]
    assert isinstance(handlers, list)
    dependencies = checked_profile["system_dependencies"]
    assert isinstance(dependencies, list)
    preserved = {DPC_APPLICATION_ID, *dependencies, *(h["package"] for h in handlers)}
    if not preserved <= installed_packages:
        raise PolicyContractError("required system package is not installed")
    data["emergency_packages"] = sorted({h["package"] for h in handlers})
    modes = data.get("modes")
    if not isinstance(modes, list):
        raise PolicyContractError("invalid policy modes")
    for mode in modes:
        if not isinstance(mode, dict):
            raise PolicyContractError("invalid policy mode")
        allowed = mode.get("allowed_packages")
        lock_task = mode.get("lock_task_packages")
        if not isinstance(allowed, list) or not isinstance(lock_task, list):
            raise PolicyContractError("invalid mode packages")
        if len(allowed) != len(set(allowed)) or len(lock_task) != len(set(lock_task)):
            raise PolicyContractError("duplicate policy package")
        requested = set(allowed) | set(lock_task)
        if not requested <= installed_packages:
            raise PolicyContractError("unknown policy package")
        if not requested - preserved <= INITIAL_EDUCATIONAL_APPS:
            raise PolicyContractError("package is not in the educational allowlist")
        mode["allowed_packages"] = sorted(requested | preserved)
        mode["lock_task_packages"] = sorted(set(lock_task) | preserved)
        blocked = mode.get("blocked_packages")
        if not isinstance(blocked, list) or len(blocked) != len(set(blocked)):
            raise PolicyContractError("invalid blocked packages")
        if set(blocked) & preserved:
            raise PolicyContractError("essential package cannot be blocked")
    if data.get("schema_version") == 3:
        from app.policy_contract_v3 import validate_policy_v3

        return validate_policy_v3(data)
    return validate_policy_v2(data)


def resolve_policy_from_certification(
    template: object,
    approved_record: object,
    *,
    installed_packages: set[str],
    verifier_key: Ed25519PublicKey,
    operator_keys: dict[str, Ed25519PublicKey],
) -> dict[str, object]:
    """Production entry point; never accept a DPC self-report as approval."""
    record = verify_certification_record(
        approved_record, verifier_key=verifier_key, operator_keys=operator_keys
    )
    payload = record["payload"]
    handlers = payload["handlers"]
    verified_handlers = {(handler["role"], handler["package"]) for handler in handlers}
    profile = {
        "model": payload["identity"]["model"],
        "handlers": [
            {
                "role": handler["role"],
                "package": handler["package"],
                "system_signed": True,
                "attested": True,
            }
            for handler in handlers
        ],
        "system_dependencies": payload["system_dependencies"],
        "emergency_call_tested": True,
    }
    return resolve_policy_for_device(
        template,
        profile,
        installed_packages=installed_packages,
        verified_handlers=verified_handlers,
    )
