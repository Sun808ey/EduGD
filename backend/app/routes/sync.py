from __future__ import annotations

from typing import cast
from uuid import UUID

from flask import Blueprint, Response, current_app, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import TooManyRequests

from app.device_identity import parse_canonical_uuid4
from app.extensions import db, limiter
from app.models import Device
from app.services.device_authentication import (
    DeviceAuthenticationContext,
    credential_rate_limit_key,
    device_authentication_required,
)
from app.services.policy_sync import (
    MAX_CURRENT_VERSION,
    AssignmentIntegrityError,
    DeviceBlockedError,
    DeviceNotFoundError,
    InvalidClientPolicyIdentityError,
    InvalidCurrentVersionError,
    InvalidDeviceUUIDError,
    PolicyInactiveError,
    PolicyRevokedError,
    PolicySyncStateError,
    RevisionMismatchError,
    SynchronizationAuditPersistenceError,
    get_policy_sync_payload,
    get_version_aware_policy_sync_payload,
    record_policy_sync_event,
)

sync_bp = Blueprint("sync", __name__)
SYNC_QUERY_NAMES = frozenset(
    {"current_version", "current_policy_uuid", "current_revision_uuid"}
)


@sync_bp.get("/sync/policies/<device_uuid>")
@device_authentication_required(allowed_query_names=SYNC_QUERY_NAMES)
@limiter.limit(
    lambda: current_app.config["POLICY_SYNC_RATE_LIMIT"],
    key_func=credential_rate_limit_key,
)
def synchronize_policy(device_uuid: str) -> tuple[Response, int]:
    current_version: int | None = None
    current_policy_uuid: UUID | None = None
    current_revision_uuid: UUID | None = None
    legacy_contract = False
    try:
        current_version = _parse_current_version()
        current_policy_uuid, current_revision_uuid = _parse_client_policy_identity(
            current_version
        )
        legacy_contract = current_version is None
        if legacy_contract:
            payload = get_policy_sync_payload(device_uuid)
            policy = payload["policy"]
            operation = "apply" if isinstance(policy, dict) else "no_change"
            server_version = policy["policy_version"] if isinstance(policy, dict) else 0
        else:
            payload = get_version_aware_policy_sync_payload(
                device_uuid,
                current_version,
                current_policy_uuid,
                current_revision_uuid,
            )
            operation = str(payload["operation"])
            server_version = cast(int, payload["server_policy_version"])
        device_id, credential_id = _audit_actor(device_uuid)
        _record_event(
            device_uuid=device_uuid,
            current_version=current_version,
            current_policy_uuid=current_policy_uuid,
            current_revision_uuid=current_revision_uuid,
            operation=operation,
            outcome=("no_assignment" if payload.get("policy") is None else "success"),
            server_version=server_version,
            device_id=device_id,
            credential_id=credential_id,
        )
        current_app.logger.info(
            "Policy synchronization completed",
            extra={"event": f"policy_sync_{operation}"},
        )
    except (InvalidCurrentVersionError, InvalidClientPolicyIdentityError) as error:
        current_app.logger.warning(
            "Policy synchronization request rejected",
            extra={"event": "policy_sync_invalid_request"},
        )
        try:
            device_id, credential_id = _audit_actor(device_uuid)
            _record_event(
                device_uuid=device_uuid,
                current_version=current_version,
                current_policy_uuid=None,
                current_revision_uuid=None,
                operation="error",
                outcome="invalid_request",
                server_version=None,
                device_id=device_id,
                credential_id=credential_id,
            )
        except SynchronizationAuditPersistenceError:
            return _audit_failure_response()
        return _error_response("invalid_request", str(error), 400)
    except InvalidDeviceUUIDError as error:
        current_app.logger.warning(
            "Policy synchronization device identity rejected",
            extra={"event": "policy_sync_invalid_device"},
        )
        try:
            _record_event(
                device_uuid=device_uuid,
                current_version=current_version,
                current_policy_uuid=current_policy_uuid,
                current_revision_uuid=current_revision_uuid,
                operation="error",
                outcome="invalid_request",
                server_version=None,
                device_id=None,
                credential_id=None,
            )
        except SynchronizationAuditPersistenceError:
            return _audit_failure_response()
        return _error_response("invalid_device_uuid", str(error), 400)
    except PolicySyncStateError as error:
        _log_state_error(error)
        try:
            _, credential_id = _audit_actor(device_uuid)
            _record_event(
                device_uuid=device_uuid,
                current_version=current_version,
                current_policy_uuid=current_policy_uuid,
                current_revision_uuid=current_revision_uuid,
                operation=error.operation,
                outcome=error.outcome_category,
                server_version=error.server_policy_version,
                device_id=error.device_id,
                credential_id=credential_id,
            )
        except SynchronizationAuditPersistenceError:
            return _audit_failure_response()
        if isinstance(error, DeviceNotFoundError):
            return _error_response(
                "sync_unavailable", "policy synchronization unavailable", 404
            )
        if isinstance(error, DeviceBlockedError):
            return _error_response(
                "device_blocked",
                "policy synchronization unavailable",
                403,
                operation="blocked",
            )
        if isinstance(error, (PolicyInactiveError, PolicyRevokedError)):
            return _error_response(
                "policy_unavailable",
                "assigned policy is unavailable",
                409,
                operation="blocked",
            )
        if isinstance(error, (AssignmentIntegrityError, RevisionMismatchError)):
            return _error_response(
                "sync_integrity_failure",
                "policy synchronization is temporarily unavailable",
                503,
                operation="error",
            )
        return _error_response(
            "sync_unavailable", "policy synchronization unavailable", 503
        )
    except SynchronizationAuditPersistenceError:
        return _audit_failure_response()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Policy synchronization database failure",
            extra={"event": "policy_sync_internal_error"},
        )
        return _error_response(
            "internal_error", "policy synchronization is temporarily unavailable", 500
        )

    response = jsonify(payload)
    if legacy_contract:
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Fri, 31 Dec 2027 23:59:59 GMT"
        response.headers["Link"] = (
            '</api/v1/docs/policy-synchronization>; rel="deprecation"'
        )
    return _no_store(response), 200


def _parse_current_version() -> int | None:
    values = request.args.getlist("current_version")
    if not values:
        return None
    if len(values) != 1:
        raise InvalidCurrentVersionError()
    value = values[0]
    if (
        not value
        or not value.isascii()
        or not value.isdigit()
        or len(value) > 10
        or (len(value) == 10 and value > str(MAX_CURRENT_VERSION))
    ):
        raise InvalidCurrentVersionError()
    return int(value)


def _parse_client_policy_identity(
    current_version: int | None,
) -> tuple[UUID | None, UUID | None]:
    policy_values = request.args.getlist("current_policy_uuid")
    revision_values = request.args.getlist("current_revision_uuid")
    if not policy_values and not revision_values:
        return None, None
    if current_version is None or len(policy_values) != 1 or len(revision_values) != 1:
        raise InvalidClientPolicyIdentityError()
    try:
        return (
            parse_canonical_uuid4(policy_values[0]),
            parse_canonical_uuid4(revision_values[0]),
        )
    except ValueError as error:
        raise InvalidClientPolicyIdentityError() from error


def _audit_actor(device_uuid: str) -> tuple[int | None, int | None]:
    context = getattr(g, "device_authentication_context", None)
    if isinstance(context, DeviceAuthenticationContext):
        return (
            context.device.id,
            context.credential.id if context.credential is not None else None,
        )
    try:
        canonical_uuid = parse_canonical_uuid4(device_uuid)
    except ValueError:
        return None, None
    device_id = db.session.scalar(
        select(Device.id).where(Device.device_uuid == canonical_uuid)
    )
    return device_id, None


def _record_event(
    *,
    device_uuid: str,
    current_version: int | None,
    current_policy_uuid: UUID | None,
    current_revision_uuid: UUID | None,
    operation: str,
    outcome: str,
    server_version: int | None,
    device_id: int | None,
    credential_id: int | None,
) -> None:
    record_policy_sync_event(
        requested_device_uuid=device_uuid,
        reported_client_version=current_version,
        reported_policy_uuid=current_policy_uuid,
        reported_revision_uuid=current_revision_uuid,
        operation=operation,
        outcome_category=outcome,
        server_policy_version=server_version,
        device_id=device_id,
        credential_id=credential_id,
    )


def _log_state_error(error: PolicySyncStateError) -> None:
    current_app.logger.warning(
        "Policy synchronization state rejected",
        extra={"event": f"policy_sync_{error.outcome_category}"},
    )


def _audit_failure_response() -> tuple[Response, int]:
    current_app.logger.exception(
        "Policy synchronization audit persistence failed",
        extra={"event": "policy_sync_audit_failure"},
    )
    return _error_response(
        "audit_unavailable",
        "policy synchronization is temporarily unavailable",
        503,
    )


def _error_response(
    code: str,
    message: str,
    status: int,
    *,
    operation: str = "error",
) -> tuple[Response, int]:
    response = jsonify(
        {
            "device_uuid": None,
            "operation": operation,
            "server_policy_version": None,
            "policy": None,
            "error": {"code": code, "message": message},
        }
    )
    return _no_store(response), status


def _no_store(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    return response


@sync_bp.errorhandler(TooManyRequests)
def handle_sync_rate_limit(_error: TooManyRequests) -> tuple[Response, int]:
    return _error_response(
        "rate_limit_exceeded",
        "policy synchronization rate limit exceeded",
        429,
    )
