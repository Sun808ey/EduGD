"""Verification contract for independently attested, dual-approved handset profiles.

Only a trusted server-side verifier can sign a verification receipt. This module
does not mint receipts from DPC assertions or perform a telephone test.
"""

from __future__ import annotations

import base64
import re
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.android_integration_config import DISCOVERY_ROLES, DPC_APPLICATION_ID
from app.policy_contract import canonical_json_bytes

_PACKAGE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_COMPONENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_.$]+$")


class CertificationError(ValueError):
    pass


def _text(value: object, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or not value.isprintable()
    ):
        raise CertificationError("invalid certification text")
    return value


def _digest(value: object) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise CertificationError("invalid SHA-256 digest")
    return value


def _date(value: object) -> str:
    value = _text(value, 10)
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError as error:
        raise CertificationError("invalid security patch") from error
    return value


def _timestamp(value: object) -> datetime:
    raw = _text(value, 32)
    if not raw.endswith("Z"):
        raise CertificationError("timestamp must be UTC")
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as error:
        raise CertificationError("invalid timestamp") from error
    if (
        parsed.tzinfo is None
        or parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        != raw
    ):
        raise CertificationError("noncanonical timestamp")
    return parsed


def validate_profile_payload(value: object) -> dict[str, Any]:
    """Validate complete build identity, workstation inventory and test evidence."""
    if not isinstance(value, dict) or set(value) != {
        "identity",
        "handlers",
        "system_dependencies",
        "baseline_sha256",
        "baseline_inventory_sha256",
        "factory_reset_reference",
        "dpc_signing_sha256",
        "attestation",
        "call_test",
        "procedure",
        "certified_at",
        "previous_record_hash",
    }:
        raise CertificationError("invalid profile fields")
    identity = value["identity"]
    keys = {
        "manufacturer",
        "model",
        "product",
        "api_level",
        "build_fingerprint",
        "security_patch",
        "carrier",
        "carrier_configuration_sha256",
    }
    if not isinstance(identity, dict) or set(identity) != keys:
        raise CertificationError("incomplete build identity")
    for key in keys - {"api_level", "security_patch", "carrier_configuration_sha256"}:
        _text(identity[key], 512 if key == "build_fingerprint" else 120)
    _digest(identity["carrier_configuration_sha256"])
    if type(identity["api_level"]) is not int or not 29 <= identity["api_level"] <= 35:
        raise CertificationError("unsupported API level")
    _date(identity["security_patch"])
    _digest(value["baseline_sha256"])
    _digest(value["baseline_inventory_sha256"])
    if value["factory_reset_reference"] is not True:
        raise CertificationError("factory-reset reference handset required")
    _digest(value["dpc_signing_sha256"])
    previous = value["previous_record_hash"]
    if previous is not None:
        _digest(previous)

    handlers = value["handlers"]
    if not isinstance(handlers, list) or len(handlers) != len(DISCOVERY_ROLES):
        raise CertificationError("incomplete handler inventory")
    roles: set[str] = set()
    for handler in handlers:
        if not isinstance(handler, dict) or set(handler) != {
            "role",
            "package",
            "component",
            "version",
            "signing_sha256",
        }:
            raise CertificationError("invalid handler inventory")
        role = handler["role"]
        if role not in DISCOVERY_ROLES or role in roles:
            raise CertificationError("duplicate or missing handler role")
        roles.add(role)
        package = _text(handler["package"], 255)
        if not _PACKAGE.fullmatch(package):
            raise CertificationError("invalid handler package")
        component = _text(handler["component"], 255)
        if not _COMPONENT.fullmatch(component):
            raise CertificationError("invalid handler component")
        _text(handler["version"], 100)
        _digest(handler["signing_sha256"])
    if roles != DISCOVERY_ROLES:
        raise CertificationError("incomplete handler roles")
    dependencies = value["system_dependencies"]
    if (
        not isinstance(dependencies, list)
        or len(dependencies) > 64
        or len(set(dependencies)) != len(dependencies)
    ):
        raise CertificationError("invalid system dependencies")
    if "com.android.systemui" not in dependencies:
        raise CertificationError("System UI is required")
    for dependency in dependencies:
        if not _PACKAGE.fullmatch(_text(dependency, 255)):
            raise CertificationError("invalid dependency package")

    attestation = value["attestation"]
    required = {
        "challenge_sha256",
        "identity_sha256",
        "baseline_sha256",
        "chain_sha256",
        "google_root_sha256",
        "verified_at",
        "revocation_checked_at",
        "security_level",
        "verified_boot",
        "device_locked",
        "dpc_package",
        "dpc_signing_sha256",
        "play_device_integrity",
        "inventory_sha256",
        "verifier_signature",
    }
    if not isinstance(attestation, dict) or set(attestation) != required:
        raise CertificationError("incomplete attestation receipt")
    for key in (
        "challenge_sha256",
        "identity_sha256",
        "baseline_sha256",
        "chain_sha256",
        "google_root_sha256",
        "inventory_sha256",
        "dpc_signing_sha256",
    ):
        _digest(attestation[key])
    if (
        attestation["identity_sha256"]
        != sha256(canonical_json_bytes(identity)).hexdigest()
        or attestation["baseline_sha256"] != value["baseline_sha256"]
    ):
        raise CertificationError("attestation identity or baseline mismatch")
    _timestamp(attestation["verified_at"])
    _timestamp(attestation["revocation_checked_at"])
    if attestation["security_level"] not in {"StrongBox", "TrustedEnvironment"}:
        raise CertificationError("hardware attestation required")
    if (
        attestation["verified_boot"] != "Verified"
        or attestation["device_locked"] is not True
        or attestation["play_device_integrity"] is not True
        or attestation["dpc_package"] != DPC_APPLICATION_ID
        or attestation["dpc_signing_sha256"] != value["dpc_signing_sha256"]
    ):
        raise CertificationError("attestation does not meet certification gate")
    inventory_hash = sha256(canonical_json_bytes(handlers)).hexdigest()
    if (
        attestation["inventory_sha256"] != inventory_hash
        or value["baseline_inventory_sha256"] != inventory_hash
    ):
        raise CertificationError("workstation inventory mismatch")
    call_test = value["call_test"]
    if not isinstance(call_test, dict) or set(call_test) != {
        "authorization_reference",
        "before",
        "during",
        "after",
        "tested_at",
    }:
        raise CertificationError("incomplete emergency test evidence")
    _text(call_test["authorization_reference"], 255)
    for phase in ("before", "during", "after"):
        if call_test[phase] != "PASS":
            raise CertificationError("emergency calling is NOT_VERIFIED")
    _timestamp(call_test["tested_at"])
    _text(value["procedure"], 2048)
    certified = _timestamp(value["certified_at"])
    verification = _timestamp(attestation["verified_at"])
    revocation = _timestamp(attestation["revocation_checked_at"])
    if (
        verification > certified
        or certified - verification > timedelta(minutes=5)
        or revocation > certified
        or certified - revocation > timedelta(hours=24)
    ):
        raise CertificationError("certification evidence is stale")
    return value


def _verify_signature(key: Ed25519PublicKey, message: bytes, encoded: object) -> None:
    if not isinstance(encoded, str):
        raise CertificationError("missing certification signature")
    try:
        signature = base64.b64decode(encoded, validate=True)
        if len(signature) != 64:
            raise ValueError()
        key.verify(signature, message)
    except (InvalidSignature, ValueError) as error:
        raise CertificationError("invalid certification signature") from error


def verify_certification_record(
    record: object,
    *,
    verifier_key: Ed25519PublicKey,
    operator_keys: dict[str, Ed25519PublicKey],
) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != {"payload", "approvals"}:
        raise CertificationError("invalid certification record")
    payload = validate_profile_payload(record["payload"])
    attestation = payload["attestation"]
    receipt = {
        key: value for key, value in attestation.items() if key != "verifier_signature"
    }
    _verify_signature(
        verifier_key, canonical_json_bytes(receipt), attestation["verifier_signature"]
    )
    approvals = record["approvals"]
    if not isinstance(approvals, list) or len(approvals) != 2:
        raise CertificationError("two approvals are required")
    identifiers: set[str] = set()
    for approval in approvals:
        if not isinstance(approval, dict) or set(approval) != {
            "operator_id",
            "signed_at",
            "signature",
        }:
            raise CertificationError("invalid approval")
        identifier = _text(approval["operator_id"], 120)
        _timestamp(approval["signed_at"])
        if identifier in identifiers or identifier not in operator_keys:
            raise CertificationError("distinct authorized operators are required")
        identifiers.add(identifier)
        _verify_signature(
            operator_keys[identifier],
            canonical_json_bytes(
                {
                    "payload": payload,
                    "operator_id": identifier,
                    "signed_at": approval["signed_at"],
                }
            ),
            approval["signature"],
        )
    return record


def verify_enrollment_match(
    approved_record: object,
    *,
    identity: object,
    handlers: object,
    dpc_signing_sha256: str,
    expected_challenge: bytes,
    fresh_receipt: object,
    verifier_key: Ed25519PublicKey,
    now: datetime | None = None,
) -> None:
    """Only a fresh server-challenged verifier receipt can match a certified build.

    Caller must consume the challenge atomically and enforce its short expiry.
    """
    if not isinstance(approved_record, dict) or not isinstance(
        approved_record.get("payload"), dict
    ):
        raise CertificationError("approved profile is required")
    profile = validate_profile_payload(approved_record["payload"])
    if identity != profile["identity"] or handlers != profile["handlers"]:
        raise CertificationError("build, carrier, patch or handler inventory changed")
    if dpc_signing_sha256 != profile["dpc_signing_sha256"]:
        raise CertificationError("DPC signing identity changed")
    if not isinstance(fresh_receipt, dict) or set(fresh_receipt) != set(
        profile["attestation"]
    ):
        raise CertificationError("fresh attestation receipt required")
    receipt = {
        key: value
        for key, value in fresh_receipt.items()
        if key != "verifier_signature"
    }
    _verify_signature(
        verifier_key, canonical_json_bytes(receipt), fresh_receipt["verifier_signature"]
    )
    checked_at = now or datetime.now(UTC)
    verified_at = _timestamp(fresh_receipt["verified_at"])
    revoked_at = _timestamp(fresh_receipt["revocation_checked_at"])
    if (
        verified_at > checked_at
        or checked_at - verified_at > timedelta(minutes=5)
        or revoked_at > checked_at
        or checked_at - revoked_at > timedelta(hours=24)
    ):
        raise CertificationError("attestation or revocation check is stale")
    if (
        len(expected_challenge) < 32
        or fresh_receipt["challenge_sha256"] != sha256(expected_challenge).hexdigest()
        or fresh_receipt["identity_sha256"]
        != sha256(canonical_json_bytes(identity)).hexdigest()
        or fresh_receipt["inventory_sha256"]
        != sha256(canonical_json_bytes(handlers)).hexdigest()
    ):
        raise CertificationError("nonce-bound attestation mismatch")
    for field in (
        "baseline_sha256",
        "google_root_sha256",
        "security_level",
        "verified_boot",
        "device_locked",
        "dpc_package",
        "dpc_signing_sha256",
        "play_device_integrity",
    ):
        if fresh_receipt[field] != profile["attestation"][field]:
            raise CertificationError("attestation properties changed")
