from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from app.device_audit_contract import DeviceAuditContractError
from app.device_status_contract import DeviceStatusContractError
from app.extensions import limiter
from app.services.device_audit_ingestion import (
    DeviceAuditConflictError,
    DeviceAuditPersistenceError,
    ingest_device_audit_batch,
)
from app.services.device_authentication import (
    credential_rate_limit_key,
    device_authentication_required,
    get_device_authentication_context,
)
from app.services.device_status import (
    DeviceStatusConflictError,
    DeviceStatusPersistenceError,
    record_check_in,
    record_policy_acknowledgement,
)

device_audit_bp = Blueprint("device_audit", __name__)


@device_audit_bp.post("/devices/<device_uuid>/audit-batches")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
@limiter.limit("12 per minute", key_func=credential_rate_limit_key)
def upload_device_audit_batch(device_uuid: str) -> Response:
    request.max_content_length = current_app.config["DEVICE_AUDIT_MAX_CONTENT_LENGTH"]
    context = get_device_authentication_context()
    if context.credential is None or str(context.device.device_uuid) != device_uuid:
        return _error("authentication_failed", "device authentication failed", 401)
    try:
        payload = request.get_json(silent=False)
        receipt = ingest_device_audit_batch(
            payload,
            device=context.device,
            credential=context.credential,
        )
    except BadRequest:
        return _error("invalid_request", "invalid audit batch", 400)
    except DeviceAuditContractError:
        return _error("invalid_audit_batch", "invalid audit batch", 400)
    except DeviceAuditConflictError:
        return _error(
            "audit_chain_conflict", "audit batch conflicts with stored evidence", 409
        )
    except DeviceAuditPersistenceError:
        return _error(
            "audit_unavailable", "audit ingestion is temporarily unavailable", 503
        )
    response = jsonify(
        {
            "batch_uuid": receipt.batch_uuid,
            "accepted_through_sequence": receipt.accepted_through_sequence,
            "chain_head": receipt.chain_head,
            "replayed": receipt.replayed,
        }
    )
    response.status_code = 200
    response.headers["Cache-Control"] = "no-store"
    return response


@device_audit_bp.post("/devices/<device_uuid>/check-ins")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
@limiter.limit("12 per minute", key_func=credential_rate_limit_key)
def submit_device_check_in(device_uuid: str) -> Response:
    return _record_status(device_uuid, acknowledgement=False)


@device_audit_bp.post("/devices/<device_uuid>/policy-acknowledgements")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
@limiter.limit("20 per minute", key_func=credential_rate_limit_key)
def acknowledge_device_policy(device_uuid: str) -> Response:
    return _record_status(device_uuid, acknowledgement=True)


def _record_status(device_uuid: str, *, acknowledgement: bool) -> Response:
    request.max_content_length = current_app.config["REGISTRATION_MAX_CONTENT_LENGTH"]
    context = get_device_authentication_context()
    if context.credential is None or str(context.device.device_uuid) != device_uuid:
        return _error("authentication_failed", "device authentication failed", 401)
    try:
        payload = request.get_json(silent=False)
        receipt = (
            record_policy_acknowledgement(
                payload, device=context.device, credential=context.credential
            )
            if acknowledgement
            else record_check_in(
                payload, device=context.device, credential=context.credential
            )
        )
    except BadRequest:
        return _error("invalid_request", "invalid device status report", 400)
    except DeviceStatusContractError:
        return _error("invalid_status_report", "invalid device status report", 400)
    except DeviceStatusConflictError:
        return _error(
            "status_conflict", "device status report conflicts with stored state", 409
        )
    except DeviceStatusPersistenceError:
        return _error(
            "status_unavailable",
            "device status reporting is temporarily unavailable",
            503,
        )
    response = jsonify(
        {
            "record_uuid": receipt.record_uuid,
            "replayed": receipt.replayed,
        }
    )
    response.status_code = 200
    response.headers["Cache-Control"] = "no-store"
    return response


def _error(code: str, message: str, status: int) -> Response:
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


__all__ = ["device_audit_bp"]
