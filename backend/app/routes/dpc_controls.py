from __future__ import annotations

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Blueprint, Response, current_app, g, request
from sqlalchemy import select

from app.admin_api import admin_error, admin_json
from app.administrator_authorization import administrator_required
from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    DeviceBlockOverride,
    DevicePolicyAssignment,
    Policy,
    PolicyRevision,
)
from app.policy_contract import canonical_json_bytes
from app.policy_contract_v3 import build_policy_v3_envelope, sign_policy_v3_envelope
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
    return g.administrator_request_context.administrator.id


def _uuid(value: str):
    return parse_canonical_uuid4(value)


def _override(value):
    return {
        "version": value.version,
        "status": value.status,
        "reason": value.reason,
        "issued_at": value.issued_at.isoformat(),
        "cleared_at": value.cleared_at.isoformat() if value.cleared_at else None,
    }


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


@dpc_controls_bp.post("/devices/<device_uuid>/usage-reports")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
def usage(device_uuid: str) -> Response:
    context = get_device_authentication_context()
    if str(context.device.device_uuid) != device_uuid:
        return admin_error("authentication_failed", "device authentication failed", 401)
    try:
        row = report_usage(context.device, request.get_json(silent=False))
        return admin_json(
            {
                "usage_date": row.usage_date.isoformat(),
                "active_minutes": row.active_minutes,
            }
        )
    except ValueError:
        return admin_error("invalid_usage_report", "invalid usage report", 400)
    except DeviceControlConflict as error:
        return admin_error("usage_conflict", str(error), 409)
    except DeviceControlError:
        return admin_error("usage_unavailable", "usage reporting unavailable", 503)


@dpc_controls_bp.get("/sync/v3/devices/<device_uuid>/state")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
def sync_v3(device_uuid: str) -> Response:
    context = get_device_authentication_context()
    if str(context.device.device_uuid) != device_uuid:
        return admin_error("authentication_failed", "device authentication failed", 401)
    raw_key = current_app.config.get("DPC_POLICY_SIGNING_PRIVATE_KEY")
    if not isinstance(raw_key, str):
        return admin_error("sync_unavailable", "v3 signing is not configured", 503)
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
        state = {
            "protocol_version": 3,
            "device_uuid": device_uuid,
            "override": _override(override) if override else None,
        }
        state["signature"] = (
            base64.urlsafe_b64encode(private.sign(canonical_json_bytes(state)))
            .rstrip(b"=")
            .decode("ascii")
        )
        return admin_json({"policy": envelope, "override_state": state})
    except (ValueError, TypeError):
        return admin_error("sync_unavailable", "v3 signing is invalid", 503)
