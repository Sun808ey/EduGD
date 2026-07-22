from __future__ import annotations

from uuid import UUID

from flask import Blueprint, Response, current_app, jsonify, request

from app.administrator_authorization import (
    administrator_required,
    get_administrator_request_context,
)
from app.enrollment_schemas import (
    EnrollmentValidationError,
    validate_reason_request,
    validate_rotation_request,
    validate_token_issue_request,
)
from app.extensions import limiter
from app.services.device_authentication import (
    credential_rate_limit_key,
    device_authentication_required,
    get_device_authentication_context,
)
from app.services.device_enrollment import (
    EnrollmentConflict,
    EnrollmentDatabaseError,
    EnrollmentFailed,
    EnrollmentNotFound,
    issue_enrollment_token,
    revoke_device_credential,
    revoke_enrollment_token,
    rotate_device_credential,
)

enrollment_bp = Blueprint("enrollment", __name__)


@enrollment_bp.post("/admin/enrollment-tokens")
@administrator_required(permission="enrollment_token.issue")
def issue_token() -> Response:
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    try:
        data = validate_token_issue_request(request)
        issued = issue_enrollment_token(
            data,
            get_administrator_request_context().administrator,
        )
    except EnrollmentValidationError as error:
        return _json_no_store({"error": "invalid_request"}, error.status_code)
    except EnrollmentNotFound:
        return _json_no_store({"error": "device_not_found"}, 404)
    except EnrollmentConflict:
        return _json_no_store({"error": "operation_not_available"}, 409)
    except EnrollmentDatabaseError:
        return _json_no_store({"error": "internal_server_error"}, 500)
    return _json_no_store(
        {
            "token_uuid": issued.token_uuid,
            "pairing_token": issued.pairing_token,
            "expires_at": issued.expires_at,
            "bound_device_uuid": issued.bound_device_uuid,
        },
        201,
    )


@enrollment_bp.post("/admin/enrollment-tokens/<token_uuid>/revoke")
@administrator_required(permission="enrollment_token.revoke")
def revoke_token(token_uuid: str) -> Response:
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    try:
        parsed_uuid = _canonical_uuid(token_uuid)
        data = validate_reason_request(request)
        revoke_enrollment_token(
            parsed_uuid,
            data.reason,
            get_administrator_request_context().administrator,
        )
    except (ValueError, EnrollmentValidationError):
        return _json_no_store({"error": "invalid_request"}, 400)
    except EnrollmentNotFound:
        return _json_no_store({"error": "enrollment_token_not_found"}, 404)
    except EnrollmentConflict:
        return _json_no_store({"error": "operation_not_available"}, 409)
    except EnrollmentDatabaseError:
        return _json_no_store({"error": "internal_server_error"}, 500)
    return _json_no_store({"message": "enrollment token revoked"}, 200)


@enrollment_bp.post("/admin/devices/<device_uuid>/credentials/revoke")
@administrator_required(permission="device_credential.revoke")
def revoke_credential(device_uuid: str) -> Response:
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    try:
        parsed_uuid = _canonical_uuid(device_uuid)
        data = validate_reason_request(request)
        revoke_device_credential(
            parsed_uuid,
            data.reason,
            get_administrator_request_context().administrator,
        )
    except (ValueError, EnrollmentValidationError):
        return _json_no_store({"error": "invalid_request"}, 400)
    except EnrollmentNotFound:
        return _json_no_store({"error": "active_credential_not_found"}, 404)
    except EnrollmentDatabaseError:
        return _json_no_store({"error": "internal_server_error"}, 500)
    return _json_no_store({"message": "device credential revoked"}, 200)


@enrollment_bp.post("/devices/<device_uuid>/credentials/rotate")
@device_authentication_required(allowed_query_names=frozenset(), allow_legacy=False)
@limiter.limit("10 per minute", key_func=credential_rate_limit_key)
def rotate_credential(device_uuid: str) -> Response:
    request.max_content_length = current_app.config["REGISTRATION_MAX_CONTENT_LENGTH"]
    context = get_device_authentication_context()
    if context.credential is None:
        return _json_no_store({"error": "authentication_failed"}, 401)
    try:
        data = validate_rotation_request(request)
        credential_uuid = rotate_device_credential(context.credential, data)
    except EnrollmentValidationError as error:
        return _json_no_store({"error": "invalid_request"}, error.status_code)
    except EnrollmentFailed:
        return _json_no_store({"error": "credential_rotation_failed"}, 401)
    except EnrollmentDatabaseError:
        return _json_no_store({"error": "internal_server_error"}, 500)
    return _json_no_store(
        {
            "device_uuid": device_uuid,
            "credential_uuid": credential_uuid,
            "credential_algorithm": "RSA_2048_SHA256",
        },
        201,
    )


def _canonical_uuid(value: str) -> UUID:
    parsed = UUID(value)
    if str(parsed) != value or parsed.version != 4:
        raise ValueError("invalid UUID")
    return parsed


def _json_no_store(payload: dict[str, object], status_code: int) -> Response:
    response = jsonify(payload)
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


__all__ = ["enrollment_bp"]
