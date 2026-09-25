"""The signed, privacy-preserving policy contract for DPC protocol v3."""

from __future__ import annotations

import base64
import hashlib
import re
from copy import deepcopy
from typing import cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.policy_contract import PolicyContractError, canonical_json_bytes
from app.protocol_versions import POLICY_PROTOCOL_VERSION, POLICY_SCHEMA_VERSION

_DOMAIN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_RULE_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


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
    if not isinstance(value, dict) or set(value) != {
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
    }:
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
    screen = value["screen_time"]
    if not isinstance(screen, dict) or set(screen) != {
        "daily_limit_minutes",
        "reset_minute",
        "exhausted_mode_id",
    }:
        raise PolicyContractError("invalid screen_time")
    limit, reset, exhausted = screen.values()
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
    return {
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
