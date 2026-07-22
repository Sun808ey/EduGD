from flask import Blueprint, Response, current_app, jsonify, request

from app.enrollment_schemas import (
    EnrollmentValidationError,
    validate_enrollment_request,
)
from app.extensions import limiter
from app.schemas import (
    DeviceRegistrationValidationError,
    validate_device_registration_request,
)
from app.services.device_enrollment import (
    EnrollmentConflict,
    EnrollmentDatabaseError,
    EnrollmentFailed,
    enroll_device,
)
from app.services.device_registration import (
    DeviceRegistrationConflictError,
    DeviceRegistrationDatabaseError,
    register_device,
)

device_bp = Blueprint("devices", __name__)


@device_bp.get("/devices")
def devices() -> Response:
    return jsonify({"message": "Device API working"})


@device_bp.post("/devices/register")
@limiter.limit("10 per minute")
def register_device_endpoint() -> tuple[Response, int]:
    request.max_content_length = current_app.config["REGISTRATION_MAX_CONTENT_LENGTH"]
    if current_app.config["DEVICE_ENROLLMENT_MODE"] != "legacy":
        return _authenticated_enrollment()
    try:
        registration_data = validate_device_registration_request(request)
    except DeviceRegistrationValidationError as error:
        return jsonify({"error": error.message}), error.status_code

    try:
        result = register_device(registration_data)
    except DeviceRegistrationConflictError as error:
        return jsonify({"error": str(error)}), 409
    except DeviceRegistrationDatabaseError:
        return jsonify({"error": "internal server error"}), 500

    message = "device registered" if result.created else "device already registered"
    status_code = 201 if result.created else 200
    return (
        jsonify(
            {
                "message": message,
                "device": result.device.to_dict(),
            }
        ),
        status_code,
    )


def _authenticated_enrollment() -> tuple[Response, int]:
    try:
        enrollment_data = validate_enrollment_request(request)
    except EnrollmentValidationError as error:
        return _no_store({"error": "invalid_request"}, error.status_code)
    try:
        result = enroll_device(enrollment_data)
    except EnrollmentFailed:
        return _no_store({"error": "enrollment_failed"}, 401)
    except EnrollmentConflict:
        return _no_store({"error": "enrollment_conflict"}, 409)
    except EnrollmentDatabaseError:
        return _no_store({"error": "internal_server_error"}, 500)
    return _no_store(
        {
            "device_uuid": result.device_uuid,
            "credential_uuid": result.credential_uuid,
            "credential_algorithm": result.credential_algorithm,
            "device_status": result.device_status,
            "server_time": result.server_time,
            "enrollment_event_uuid": result.enrollment_event_uuid,
        },
        201,
    )


def _no_store(payload: dict[str, object], status_code: int) -> tuple[Response, int]:
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status_code
