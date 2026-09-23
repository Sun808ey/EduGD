from __future__ import annotations

import base64
import hashlib
from copy import deepcopy
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from app.policy_contract import (
    DPC_PROTOCOL_VERSION,
    canonical_json_bytes,
)

MAX_EVENTS_PER_BATCH = 200
MAX_METADATA_ENTRIES = 16
MAX_METADATA_TEXT = 256
EVENT_CODES = frozenset(
    {
        "policy_block",
        "enforcement_failure",
        "tamper_attempt",
        "configuration_changed",
        "policy_verified",
        "policy_applied",
        "policy_rejected",
        "sync_succeeded",
        "sync_failed",
        "clock_anomaly",
        "boot_observed",
        "policy_stale",
        "screen_time_exhausted",
        "web_filter_blocked",
        "block_override_applied",
        "block_override_cleared",
    }
)
OUTCOMES = frozenset({"allowed", "blocked", "succeeded", "failed", "detected"})
_EVENT_KEYS = frozenset(
    {
        "event_uuid",
        "sequence",
        "occurred_at",
        "elapsed_realtime_ms",
        "boot_count",
        "event_code",
        "outcome",
        "policy_uuid",
        "revision_uuid",
        "rule_id",
        "metadata",
        "previous_event_hash",
    }
)
_BATCH_KEYS = frozenset(
    {
        "protocol_version",
        "batch_uuid",
        "device_uuid",
        "credential_uuid",
        "first_sequence",
        "last_sequence",
        "previous_head",
        "final_head",
        "signature_algorithm",
        "events",
    }
)


class DeviceAuditContractError(ValueError):
    pass


def _uuid(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise DeviceAuditContractError(f"invalid {field}")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise DeviceAuditContractError(f"invalid {field}") from error
    if parsed.version != 4 or str(parsed) != value:
        raise DeviceAuditContractError(f"invalid {field}")
    return value


def _optional_uuid(value: object, field: str) -> str | None:
    return None if value is None else _uuid(value, field)


def _integer(value: object, field: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise DeviceAuditContractError(f"invalid {field}")
    return value


def _hash(value: object, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or len(value) != 64:
        raise DeviceAuditContractError(f"invalid {field}")
    try:
        bytes.fromhex(value)
    except ValueError as error:
        raise DeviceAuditContractError(f"invalid {field}") from error
    if value != value.lower():
        raise DeviceAuditContractError(f"invalid {field}")
    return value


def _timestamp(value: object) -> str:
    # Reuse the policy envelope's exact timestamp contract without exposing its helper.
    from datetime import UTC, datetime

    if not isinstance(value, str) or not value.endswith("Z"):
        raise DeviceAuditContractError("invalid occurred_at")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise DeviceAuditContractError("invalid occurred_at") from error
    if parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise DeviceAuditContractError("invalid occurred_at")
    return value


def _metadata(value: object) -> dict[str, bool | int | str | None]:
    if not isinstance(value, dict) or len(value) > MAX_METADATA_ENTRIES:
        raise DeviceAuditContractError("invalid metadata")
    result: dict[str, bool | int | str | None] = {}
    for key, item in value.items():
        if (
            not isinstance(key, str)
            or not key
            or len(key) > 64
            or not key.replace("_", "a").isalnum()
        ):
            raise DeviceAuditContractError("invalid metadata key")
        if item is None or isinstance(item, bool):
            result[key] = item
        elif (
            isinstance(item, int)
            and not isinstance(item, bool)
            and -(2**63) <= item < 2**63
        ):
            result[key] = item
        elif (
            isinstance(item, str)
            and len(item) <= MAX_METADATA_TEXT
            and item.isprintable()
        ):
            result[key] = item
        else:
            raise DeviceAuditContractError("invalid metadata value")
    return {key: result[key] for key in sorted(result)}


def build_audit_event(
    *,
    event_uuid: str,
    sequence: int,
    occurred_at: str,
    elapsed_realtime_ms: int,
    boot_count: int,
    event_code: str,
    outcome: str,
    policy_uuid: str | None,
    revision_uuid: str | None,
    rule_id: str | None,
    metadata: object,
    previous_event_hash: str | None,
) -> dict[str, object]:
    if event_code not in EVENT_CODES:
        raise DeviceAuditContractError("invalid event_code")
    if outcome not in OUTCOMES:
        raise DeviceAuditContractError("invalid outcome")
    if rule_id is not None and (
        not isinstance(rule_id, str)
        or not 1 <= len(rule_id) <= 64
        or not rule_id.replace("_", "a").isalnum()
    ):
        raise DeviceAuditContractError("invalid rule_id")
    event: dict[str, object] = {
        "event_uuid": _uuid(event_uuid, "event_uuid"),
        "sequence": _integer(sequence, "sequence", 1, 2**63 - 1),
        "occurred_at": _timestamp(occurred_at),
        "elapsed_realtime_ms": _integer(
            elapsed_realtime_ms, "elapsed_realtime_ms", 0, 2**63 - 1
        ),
        "boot_count": _integer(boot_count, "boot_count", 0, 2**31 - 1),
        "event_code": event_code,
        "outcome": outcome,
        "policy_uuid": _optional_uuid(policy_uuid, "policy_uuid"),
        "revision_uuid": _optional_uuid(revision_uuid, "revision_uuid"),
        "rule_id": rule_id,
        "metadata": _metadata(metadata),
        "previous_event_hash": _hash(
            previous_event_hash, "previous_event_hash", nullable=True
        ),
    }
    if (event["policy_uuid"] is None) != (event["revision_uuid"] is None):
        raise DeviceAuditContractError("policy and revision identity must be paired")
    event["event_hash"] = hashlib.sha256(canonical_json_bytes(event)).hexdigest()
    if event_code == "web_filter_blocked":
        # Raw domains and URLs are intentionally not accepted into forensic evidence.
        metadata = event["metadata"]
        assert isinstance(metadata, dict)
        if set(metadata) != {"domain_hash"} or not _hash(
            metadata["domain_hash"], "domain_hash"
        ):
            raise DeviceAuditContractError("web filter evidence must contain only domain_hash")
    return event


def validate_audit_event(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _EVENT_KEYS | {"event_hash"}:
        raise DeviceAuditContractError("invalid audit event")
    rebuilt = build_audit_event(**{key: value[key] for key in _EVENT_KEYS})
    supplied_hash = _hash(value["event_hash"], "event_hash")
    if supplied_hash != rebuilt["event_hash"]:
        raise DeviceAuditContractError("audit event hash mismatch")
    return rebuilt


def build_audit_batch(
    *,
    batch_uuid: str,
    device_uuid: str,
    credential_uuid: str,
    signature_algorithm: str,
    events: object,
) -> dict[str, object]:
    if signature_algorithm not in {"ECDSA_P256_SHA256", "RSA_2048_SHA256"}:
        raise DeviceAuditContractError("unsupported signature algorithm")
    if not isinstance(events, list) or not 1 <= len(events) <= MAX_EVENTS_PER_BATCH:
        raise DeviceAuditContractError("invalid audit event batch")
    checked = [validate_audit_event(event) for event in events]
    for index, event in enumerate(checked):
        if index:
            previous_sequence = checked[index - 1]["sequence"]
            assert isinstance(previous_sequence, int)
            if event["sequence"] != previous_sequence + 1:
                raise DeviceAuditContractError("audit sequence gap")
        expected_previous = None if index == 0 else checked[index - 1]["event_hash"]
        if index and event["previous_event_hash"] != expected_previous:
            raise DeviceAuditContractError("audit chain mismatch")
    return {
        "protocol_version": DPC_PROTOCOL_VERSION,
        "batch_uuid": _uuid(batch_uuid, "batch_uuid"),
        "device_uuid": _uuid(device_uuid, "device_uuid"),
        "credential_uuid": _uuid(credential_uuid, "credential_uuid"),
        "first_sequence": checked[0]["sequence"],
        "last_sequence": checked[-1]["sequence"],
        "previous_head": checked[0]["previous_event_hash"],
        "final_head": checked[-1]["event_hash"],
        "signature_algorithm": signature_algorithm,
        "events": checked,
    }


def _validate_batch(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _BATCH_KEYS:
        raise DeviceAuditContractError("invalid audit batch")
    if value["protocol_version"] != DPC_PROTOCOL_VERSION:
        raise DeviceAuditContractError("unsupported protocol version")
    rebuilt = build_audit_batch(
        batch_uuid=value["batch_uuid"],
        device_uuid=value["device_uuid"],
        credential_uuid=value["credential_uuid"],
        signature_algorithm=value["signature_algorithm"],
        events=value["events"],
    )
    for field in ("first_sequence", "last_sequence", "previous_head", "final_head"):
        if value[field] != rebuilt[field]:
            raise DeviceAuditContractError(f"audit batch {field} mismatch")
    return rebuilt


def sign_audit_batch(
    batch: object, private_key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey
) -> dict[str, object]:
    checked = _validate_batch(batch)
    data = canonical_json_bytes(checked)
    if checked["signature_algorithm"] == "ECDSA_P256_SHA256":
        if not isinstance(private_key, ec.EllipticCurvePrivateKey) or not isinstance(
            private_key.curve, ec.SECP256R1
        ):
            raise DeviceAuditContractError("signature key does not match algorithm")
        signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))
    else:
        if (
            not isinstance(private_key, rsa.RSAPrivateKey)
            or private_key.key_size != 2048
        ):
            raise DeviceAuditContractError("signature key does not match algorithm")
        signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    return {
        **deepcopy(checked),
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii"),
    }


def verify_audit_batch(
    signed_batch: object,
    public_key: ec.EllipticCurvePublicKey | rsa.RSAPublicKey,
    *,
    expected_previous_head: str | None,
    expected_first_sequence: int,
) -> dict[str, object]:
    if not isinstance(signed_batch, dict) or set(signed_batch) != _BATCH_KEYS | {
        "signature"
    }:
        raise DeviceAuditContractError("invalid signed audit batch")
    unsigned = {key: signed_batch[key] for key in _BATCH_KEYS}
    checked = _validate_batch(unsigned)
    if checked["previous_head"] != expected_previous_head:
        raise DeviceAuditContractError("audit batch does not continue stored chain")
    if checked["first_sequence"] != expected_first_sequence:
        raise DeviceAuditContractError("audit batch does not continue stored sequence")
    signature_text = signed_batch["signature"]
    if not isinstance(signature_text, str):
        raise DeviceAuditContractError("invalid audit batch signature")
    try:
        signature = base64.urlsafe_b64decode(
            signature_text + "=" * (-len(signature_text) % 4)
        )
        if (
            base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
            != signature_text
        ):
            raise ValueError
        data = canonical_json_bytes(checked)
        if checked["signature_algorithm"] == "ECDSA_P256_SHA256":
            if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(
                public_key.curve, ec.SECP256R1
            ):
                raise DeviceAuditContractError(
                    "verification key does not match algorithm"
                )
            public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
        else:
            if (
                not isinstance(public_key, rsa.RSAPublicKey)
                or public_key.key_size != 2048
            ):
                raise DeviceAuditContractError(
                    "verification key does not match algorithm"
                )
            public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
    except (ValueError, InvalidSignature) as error:
        raise DeviceAuditContractError("invalid audit batch signature") from error
    return checked


__all__ = [
    "DeviceAuditContractError",
    "build_audit_batch",
    "build_audit_event",
    "sign_audit_batch",
    "validate_audit_event",
    "verify_audit_batch",
]
