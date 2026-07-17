from flask import Blueprint, Response, jsonify, request

from app.schemas import (
    DeviceRegistrationValidationError,
    validate_device_registration_request,
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
def register_device_endpoint() -> tuple[Response, int]:
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
