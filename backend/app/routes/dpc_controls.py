from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Blueprint, Response, current_app, g, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.admin_api import (
    AdminRequestError,
    admin_error,
    admin_json,
    isoformat_utc,
    pagination_payload,
    parse_pagination,
)
from app.administrator_authorization import administrator_required
from app.device_api import device_error, device_json
from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    DeviceBlockOverride,
    DeviceControlEvent,
    DevicePolicyAssignment,
    DeviceUsageDaily,
    DeviceWebFilterEvent,
    Policy,
    PolicyApplicationEvent,
    PolicyRevision,
)
from app.policy_contract import canonical_json_bytes
from app.policy_contract_v3 import build_policy_v3_envelope, sign_policy_v3_envelope
from app.protocol_versions import CONTROL_STATE_PROTOCOL_VERSION
from app.services.device_authentication import (
    device_authentication_required,
    get_device_authentication_context,
)
from app.services.device_controls import (
    DeviceControlConflict,
    DeviceControlError,
    DeviceControlNotFound,
    clear_block,
    report_usage,
    set_block,
)

dpc_controls_bp = Blueprint("dpc_controls", __name__)


def _admin_context_id() -> int:
    return int(g.administrator_request_context.administrator.id)


def _uuid(value: str) -> UUID:
    return parse_canonical_uuid4(value)


def _override(value: DeviceBlockOverride) -> dict[str, Any]:
    return {
        "version": value.version,
        "status": value.status,
        "reason": value.reason,
        "issued_at": value.issued_at.isoformat(),
        "cleared_at": value.cleared_at.isoformat() if value.cleared_at else None,
    }


def _evidence_item(kind: str, row: object) -> dict[str, object]:
    if isinstance(row, DeviceUsageDaily):
        return {
            "kind": kind,
            "occurred_at": isoformat_utc(row.reported_at),
            "usage_date": row.usage_date.isoformat(),
            "active_minutes": row.active_minutes,
            "policy_uuid": str(row.policy_uuid),
            "revision_uuid": str(row.revision_uuid),
        }
    if isinstance(row, DeviceControlEvent):
        return {
            "kind": kind,
            "occurred_at": isoformat_utc(row.created_at),
            "operation": row.operation,
            "reason": row.reason,
        }
    if isinstance(row, DeviceWebFilterEvent):
        return {
            "kind": kind,
            "occurred_at": isoformat_utc(row.observed_at),
            "domain_hash": row.domain_hash.hex(),
            "rule_id": row.rule_id,
            "outcome": row.outcome,
            "policy_uuid": str(row.policy_uuid),
            "revision_uuid": str(row.revision_uuid),
        }
    if isinstance(row, PolicyApplicationEvent):
        return {
            "kind": kind,
            "occurred_at": isoformat_utc(row.observed_at),
            "outcome": row.outcome,
            "error_code": row.error_code,
            "policy_uuid": str(row.policy_uuid) if row.policy_uuid else None,
            "revision_uuid": str(row.revision_uuid) if row.revision_uuid else None,
        }
    raise TypeError("unsupported evidence")


@dpc_controls_bp.post("/admin/devices/<device_uuid>/block-overrides")
@administrator_required("device.control")
def block(device_uuid: str) -> Response:
    try:
        return admin_json(
            {
                "override": _override(
                    set_block(
                        _uuid(device_uuid),
                        _admin_context_id(),
                        request.get_json(silent=False).get("reason"),
                    )
                )
            },
            201,
        )
    except ValueError:
        return admin_error("invalid_request", "invalid device UUID or reason", 400)
    except DeviceControlNotFound:
        return admin_error("device_not_found", "device not found", 404)
    except DeviceControlConflict as error:
        return admin_error("control_conflict", str(error), 409)
    except DeviceControlError:
        return admin_error(
            "control_unavailable", "device control is temporarily unavailable", 503
        )


@dpc_controls_bp.post("/admin/devices/<device_uuid>/block-overrides/clear")
@administrator_required("device.control")
def unblock(device_uuid: str) -> Response:
    try:
        return admin_json(
            {
                "override": _override(
                    clear_block(
                        _uuid(device_uuid),
                        _admin_context_id(),
                        request.get_json(silent=False).get("reason"),
                    )
                )
            }
        )
    except ValueError:
        return admin_error("invalid_request", "invalid device UUID or reason", 400)
    except DeviceControlNotFound:
        return admin_error("device_not_found", "device not found", 404)
    except DeviceControlConflict as error:
        return admin_error("control_conflict", str(error), 409)
    except DeviceControlError:
        return admin_error(
            "control_unavailable", "device control is temporarily unavailable", 503
        )


@dpc_controls_bp.get("/admin/devices/<device_uuid>/block-overrides")
@administrator_required()
def get_block_override(device_uuid: str) -> Response:
    try:
        from app.models import Device

        device = db.session.scalar(
            select(Device).where(Device.device_uuid == _uuid(device_uuid))
        )
        if device is None:
            return admin_error("device_not_found", "device not found", 404)
        override = db.session.scalar(
            select(DeviceBlockOverride).where(
                DeviceBlockOverride.device_id == device.id
            )
        )
        return admin_json({"override": _override(override) if override else None})
    except ValueError:
        return admin_error("invalid_device_uuid", "device_uuid must be a UUIDv4", 400)


@dpc_controls_bp.get("/admin/devices/<device_uuid>/control-evidence")
@administrator_required()
def control_evidence(device_uuid: str) -> Response:
    try:
        from app.models import Device

        pagination = parse_pagination()
        device = db.session.scalar(
            select(Device).where(Device.device_uuid == _uuid(device_uuid))
        )
        if device is None:
            return admin_error("device_not_found", "device not found", 404)
        limit = pagination.offset + pagination.per_page
        items: list[dict[str, object]] = []
        for kind, model, timestamp in (
            ("usage", DeviceUsageDaily, DeviceUsageDaily.reported_at),
            ("override", DeviceControlEvent, DeviceControlEvent.created_at),
            ("web_filter", DeviceWebFilterEvent, DeviceWebFilterEvent.observed_at),
            (
                "policy_application",
                PolicyApplicationEvent,
                PolicyApplicationEvent.observed_at,
            ),
        ):
            rows = db.session.scalars(
                select(model)
                .where(model.device_id == device.id)
                .order_by(timestamp.desc())
                .limit(limit)
            ).all()
            items.extend(_evidence_item(kind, row) for row in rows)
        items.sort(key=lambda item: str(item["occurred_at"]), reverse=True)
        total = len(items)
        return admin_json(
            {
                "evidence": items[
                    pagination.offset : pagination.offset + pagination.per_page
                ],
                "pagination": pagination_payload(pagination, total=total),
            }
        )
    except (ValueError, AdminRequestError):
        return admin_error("invalid_request", "invalid evidence request", 400)


@dpc_controls_bp.get("/admin/dashboard/dpc-summary")
@administrator_required()
def dpc_summary() -> Response:
    try:
        from app.models import Device

        return admin_json(
            {
                "summary": {
                    "managed_devices": int(
                        db.session.scalar(select(func.count()).select_from(Device)) or 0
                    ),
                    "active_block_overrides": int(
                        db.session.scalar(
                            select(func.count())
                            .select_from(DeviceBlockOverride)
                            .where(DeviceBlockOverride.status == "active")
                        )
                        or 0
                    ),
                    "active_v3_assignments": int(
                        db.session.scalar(
                            select(func.count())
                            .select_from(DevicePolicyAssignment)
                            .join(PolicyRevision)
                            .where(
                                DevicePolicyAssignment.status == "active",
                                PolicyRevision._payload["schema_version"].as_integer()
                                == 3,
                            )
                        )
                        or 0
                    ),
                    "enforcement_failures": int(
                        db.session.scalar(
                            select(func.count())
                            .select_from(PolicyApplicationEvent)
                            .where(
                                PolicyApplicationEvent.outcome.in_(
                                    ("failed", "rejected")
                                )
                            )
                        )
                        or 0
                    ),
                }
            }
        )
    except Exception:
        return admin_error(
            "read_unavailable", "dashboard is temporarily unavailable", 503
        )


@dpc_controls_bp.post("/devices/<device_uuid>/usage-reports")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
def usage(device_uuid: str) -> Response:
    context = get_device_authentication_context()
    if str(context.device.device_uuid) != device_uuid:
        return device_error("authentication_failed", 401)
    try:
        row = report_usage(context.device, request.get_json(silent=False))
        return device_json(
            {
                "usage_date": row.usage_date.isoformat(),
                "active_minutes": row.active_minutes,
            }
        )
    except ValueError:
        return device_error("invalid_usage_report", 400)
    except DeviceControlConflict:
        return device_error("usage_conflict", 409)
    except DeviceControlError:
        return device_error("usage_unavailable", 503)


@dpc_controls_bp.post("/devices/<device_uuid>/web-filter-events")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
def web_filter_event(device_uuid: str) -> Response:
    context = get_device_authentication_context()
    if str(context.device.device_uuid) != device_uuid:
        return device_error("authentication_failed", 401)
    try:
        payload = request.get_json(silent=False)
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {
                "event_uuid",
                "domain_hash",
                "rule_id",
                "outcome",
                "policy_uuid",
                "revision_uuid",
                "observed_at",
            }
            or payload["outcome"] != "blocked"
        ):
            raise ValueError
        domain_hash = bytes.fromhex(str(payload["domain_hash"]))
        if (
            len(domain_hash) != 32
            or not isinstance(payload["rule_id"], str)
            or not 1 <= len(payload["rule_id"]) <= 64
        ):
            raise ValueError
        event_uuid = _uuid(str(payload["event_uuid"]))
        row = DeviceWebFilterEvent(
            event_uuid=event_uuid,
            device_id=context.device.id,
            domain_hash=domain_hash,
            rule_id=payload["rule_id"],
            outcome="blocked",
            policy_uuid=_uuid(str(payload["policy_uuid"])),
            revision_uuid=_uuid(str(payload["revision_uuid"])),
            observed_at=datetime.fromisoformat(
                str(payload["observed_at"]).replace("Z", "+00:00")
            ),
        )
        try:
            db.session.add(row)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = db.session.scalar(
                select(DeviceWebFilterEvent).where(
                    DeviceWebFilterEvent.event_uuid == event_uuid
                )
            )
            if existing is not None and (
                existing.device_id == context.device.id
                and existing.domain_hash == domain_hash
                and existing.rule_id == payload["rule_id"]
                and existing.outcome == "blocked"
                and str(existing.policy_uuid) == str(payload["policy_uuid"])
                and str(existing.revision_uuid) == str(payload["revision_uuid"])
                and existing.observed_at == row.observed_at
            ):
                return device_json({"event_uuid": str(event_uuid), "replayed": True})
            return device_error("web_filter_event_conflict", 409)
        return device_json({"event_uuid": str(row.event_uuid), "replayed": False}, 201)
    except Exception:
        db.session.rollback()
        return device_error("invalid_web_filter_event", 400)


@dpc_controls_bp.get("/sync/v3/devices/<device_uuid>/state")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
def sync_v3(device_uuid: str) -> Response:
    context = get_device_authentication_context()
    if str(context.device.device_uuid) != device_uuid:
        return device_error("authentication_failed", 401)
    raw_key = current_app.config.get("DPC_POLICY_SIGNING_PRIVATE_KEY")
    if not isinstance(raw_key, str):
        return device_error("sync_unavailable", 503)
    try:
        private = Ed25519PrivateKey.from_private_bytes(
            base64.urlsafe_b64decode(raw_key + "=" * (-len(raw_key) % 4))
        )
        assignment = db.session.scalar(
            select(DevicePolicyAssignment)
            .where(
                DevicePolicyAssignment.device_id == context.device.id,
                DevicePolicyAssignment.status == "active",
            )
            .order_by(DevicePolicyAssignment.id.desc())
        )
        envelope = None
        if assignment is not None:
            revision, policy = db.session.execute(
                select(PolicyRevision, Policy)
                .join(Policy)
                .where(PolicyRevision.id == assignment.policy_revision_id)
            ).one()
            if revision.payload.get("schema_version") == 3:
                envelope = sign_policy_v3_envelope(
                    build_policy_v3_envelope(
                        policy_uuid=str(policy.policy_uuid),
                        revision_uuid=str(revision.revision_uuid),
                        revision_number=revision.version,
                        issued_at=revision.created_at.astimezone().strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        signing_key_id=current_app.config["DPC_POLICY_SIGNING_KEY_ID"],
                        payload=revision.payload,
                    ),
                    private,
                )
        override = db.session.scalar(
            select(DeviceBlockOverride).where(
                DeviceBlockOverride.device_id == context.device.id
            )
        )
        operation = "apply" if envelope is not None else "clear"
        if override is not None and override.status == "active":
            operation = "blocked"
        state = {
            "protocol_version": CONTROL_STATE_PROTOCOL_VERSION,
            "device_uuid": device_uuid,
            "operation": operation,
            "signing_key_id": current_app.config["DPC_POLICY_SIGNING_KEY_ID"],
            "issued_at": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "policy_uuid": envelope["policy_uuid"] if envelope else None,
            "revision_uuid": envelope["revision_uuid"] if envelope else None,
            "override": _override(override) if override else None,
        }
        state["signature"] = (
            base64.urlsafe_b64encode(private.sign(canonical_json_bytes(state)))
            .rstrip(b"=")
            .decode("ascii")
        )
        return device_json({"policy": envelope, "state": state})
    except (ValueError, TypeError):
        return device_error("sync_unavailable", 503)
