from datetime import date
from uuid import UUID

from flask import Blueprint, Response, current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.admin_api import (
    AdminRequestError,
    admin_error,
    admin_json,
    parse_optional_filter,
    parse_pagination,
)
from app.administrator_authorization import (
    administrator_required,
    get_administrator_request_context,
)
from app.enrollment_schemas import (
    EnrollmentValidationError,
    validate_enrollment_request,
)
from app.extensions import db, limiter
from app.models import DEVICE_STATUSES, Device, DeviceLocationAssignment
from app.schemas import (
    DeviceRegistrationValidationError,
    validate_device_registration_request,
)
from app.services.admin_read import (
    AdminReadNotFoundError,
    AdminReadPersistenceError,
    get_device,
    get_device_policy_assignment,
    list_devices,
)
from app.services.device_asset_privacy import (
    DeviceAssetConflict,
    DeviceAssetNotFound,
    DeviceAssetPrivacyError,
    DeviceAssetRetentionError,
    correct_device_asset,
    correct_location_assignment,
    redact_retired_device,
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
from app.services.school_device_assets import (
    AssetRegistrationConflict,
    AssetRegistrationError,
    register_asset,
)

device_bp = Blueprint("devices", __name__)
_ASSET_FIELDS = {
    "asset_number",
    "manufacturer",
    "model",
    "serial_number",
    "android_version",
    "api_level",
    "date_received",
    "condition",
    "department",
    "asset_lifecycle_status",
    "asset_notes",
}


@device_bp.get("/devices")
def devices() -> Response:
    return jsonify({"message": "Device API working"})


@device_bp.get("/admin/devices")
@administrator_required()
def admin_devices() -> Response:
    try:
        pagination = parse_pagination()
        status = parse_optional_filter("status", DEVICE_STATUSES)
        page = list_devices(pagination, status=status)
    except AdminRequestError as error:
        return admin_error(error.code, error.message, error.status_code)
    except AdminReadPersistenceError:
        return admin_error(
            "read_unavailable", "devices are temporarily unavailable", 503
        )
    return admin_json({"devices": page.items, "pagination": page.pagination})


@device_bp.get("/admin/devices/<device_uuid>")
@administrator_required()
def admin_device_detail(device_uuid: str) -> Response:
    try:
        device = get_device(device_uuid)
    except ValueError:
        return admin_error("invalid_device_uuid", "device_uuid must be a UUIDv4", 400)
    except AdminReadNotFoundError:
        return admin_error("device_not_found", "device not found", 404)
    except AdminReadPersistenceError:
        return admin_error("read_unavailable", "device is temporarily unavailable", 503)
    return admin_json({"device": device})


@device_bp.post("/admin/devices/assets")
@administrator_required(permission="policy.manage")
def create_school_device_asset() -> Response:
    request.max_content_length = current_app.config[
        "ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH"
    ]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != _ASSET_FIELDS:
        return admin_error(
            "invalid_device_asset", "invalid device asset registration request", 400
        )
    try:
        device = register_asset(payload)
    except AssetRegistrationConflict:
        return admin_error(
            "device_asset_conflict", "asset number or serial number already exists", 409
        )
    except AssetRegistrationError:
        return admin_error(
            "invalid_device_asset", "invalid device asset registration request", 400
        )
    return admin_json({"device_uuid": str(device.device_uuid)}, 201)


@device_bp.patch("/admin/devices/<device_uuid>/asset")
@administrator_required(permission="policy.manage")
def correct_school_device_asset(device_uuid: str) -> Response:
    request.max_content_length = current_app.config[
        "ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH"
    ]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return admin_error(
            "invalid_device_asset", "invalid device asset correction request", 400
        )
    try:
        device = correct_device_asset(
            device_uuid,
            payload,
            administrator_id=get_administrator_request_context().administrator.id,
        )
    except DeviceAssetNotFound:
        return admin_error("device_not_found", "device not found", 404)
    except DeviceAssetConflict:
        return admin_error(
            "device_asset_conflict", "asset number or serial number already exists", 409
        )
    except DeviceAssetPrivacyError:
        return admin_error(
            "invalid_device_asset", "invalid device asset correction request", 400
        )
    return admin_json(
        {"device_uuid": str(device.device_uuid), "message": "device asset corrected"}
    )


@device_bp.post("/admin/devices/<device_uuid>/data-retention/purge")
@administrator_required(permission="policy.manage")
def purge_retired_device_data(device_uuid: str) -> Response:
    request.max_content_length = current_app.config[
        "ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH"
    ]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"reason"}:
        return admin_error(
            "invalid_retention_request", "a retention reason is required", 400
        )
    try:
        device = redact_retired_device(
            device_uuid,
            administrator_id=get_administrator_request_context().administrator.id,
            reason=payload["reason"],
        )
    except DeviceAssetNotFound:
        return admin_error("device_not_found", "device not found", 404)
    except DeviceAssetRetentionError as error:
        return admin_error("retention_not_ready", str(error), 409)
    except DeviceAssetPrivacyError:
        return admin_error(
            "invalid_retention_request", "invalid retention request", 400
        )
    return admin_json(
        {
            "device_uuid": str(device.device_uuid),
            "message": "retired asset data redacted",
        }
    )


@device_bp.get("/admin/devices/<device_uuid>/policy-assignment")
@administrator_required()
def admin_device_policy_assignment(device_uuid: str) -> Response:
    try:
        assignment = get_device_policy_assignment(device_uuid)
    except ValueError:
        return admin_error("invalid_device_uuid", "device_uuid must be a UUIDv4", 400)
    except AdminReadNotFoundError:
        return admin_error("device_not_found", "device not found", 404)
    except AdminReadPersistenceError:
        return admin_error(
            "read_unavailable", "policy assignment is temporarily unavailable", 503
        )
    return admin_json({"policy_assignment": assignment})


@device_bp.get("/admin/devices/<device_uuid>/location-assignments")
@administrator_required()
def device_location_assignments(device_uuid: str) -> Response:
    try:
        parsed = UUID(device_uuid)
        rows = db.session.scalars(
            select(DeviceLocationAssignment)
            .join(Device)
            .where(Device.device_uuid == parsed)
            .order_by(DeviceLocationAssignment.assigned_at.desc())
        ).all()
    except (ValueError, SQLAlchemyError):
        return admin_error("invalid_request", "device assignments are unavailable", 400)
    return admin_json({"assignments": [_assignment(row) for row in rows]})


@device_bp.post("/admin/devices/<device_uuid>/location-assignments")
@administrator_required(permission="policy.manage")
def create_device_location_assignment(device_uuid: str) -> Response:
    try:
        parsed = UUID(device_uuid)
        payload = request.get_json(silent=False)
        fields = {
            "target_type",
            "target_name",
            "responsible_officer",
            "assigned_at",
            "expected_return_date",
            "issue_condition",
        }
        if not isinstance(payload, dict) or set(payload) != fields:
            raise ValueError
        device = db.session.scalar(select(Device).where(Device.device_uuid == parsed))
        if device is None:
            return admin_error("device_not_found", "device not found", 404)
        row = DeviceLocationAssignment(
            device_id=device.id,
            target_type=_text(payload["target_type"], 16),
            target_name=_text(payload["target_name"], 120),
            responsible_officer=_text(payload["responsible_officer"], 120),
            assigned_at=date.fromisoformat(str(payload["assigned_at"])),
            expected_return_date=date.fromisoformat(
                str(payload["expected_return_date"])
            )
            if payload["expected_return_date"]
            else None,
            issue_condition=_text(payload["issue_condition"], 80),
            recorded_by_administrator_id=get_administrator_request_context().administrator.id,
        )
        db.session.add(row)
        db.session.commit()
        return admin_json({"assignment": _assignment(row)}, 201)
    except (ValueError, TypeError):
        db.session.rollback()
        return admin_error("invalid_assignment", "invalid device assignment", 400)
    except IntegrityError:
        db.session.rollback()
        return admin_error(
            "assignment_conflict", "device already has an active assignment", 409
        )


@device_bp.patch("/admin/devices/<device_uuid>/location-assignments/<assignment_uuid>")
@administrator_required(permission="policy.manage")
def correct_device_location_assignment(
    device_uuid: str, assignment_uuid: str
) -> Response:
    request.max_content_length = current_app.config[
        "ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH"
    ]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return admin_error(
            "invalid_assignment", "invalid device assignment correction", 400
        )
    try:
        row = correct_location_assignment(
            device_uuid,
            assignment_uuid,
            payload,
            administrator_id=get_administrator_request_context().administrator.id,
        )
    except DeviceAssetNotFound:
        return admin_error("assignment_not_found", "device assignment not found", 404)
    except DeviceAssetPrivacyError:
        return admin_error(
            "invalid_assignment", "invalid device assignment correction", 400
        )
    return admin_json({"assignment": _assignment(row)})


def _text(value: object, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= maximum
        or not value.isprintable()
    ):
        raise ValueError
    return value.strip()


def _assignment(row: DeviceLocationAssignment) -> dict[str, object]:
    return {
        "assignment_uuid": str(row.assignment_uuid),
        "target_type": row.target_type,
        "target_name": row.target_name,
        "responsible_officer": row.responsible_officer,
        "assigned_at": row.assigned_at.isoformat(),
        "expected_return_date": row.expected_return_date.isoformat()
        if row.expected_return_date
        else None,
        "returned_at": row.returned_at.isoformat() if row.returned_at else None,
        "issue_condition": row.issue_condition,
        "return_condition": row.return_condition,
    }


@device_bp.post("/devices/register")
@limiter.limit("10 per minute")
def register_device_endpoint() -> tuple[Response, int]:
    request.max_content_length = current_app.config["REGISTRATION_MAX_CONTENT_LENGTH"]
    if current_app.config["DEVICE_ENROLLMENT_MODE"] != "legacy":
        return _authenticated_enrollment()
    try:
        registration_data = validate_device_registration_request(request)
    except DeviceRegistrationValidationError as error:
        return _no_store({"error": error.message}, error.status_code)

    try:
        result = register_device(registration_data)
    except DeviceRegistrationConflictError as error:
        return _no_store({"error": str(error)}, 409)
    except DeviceRegistrationDatabaseError:
        return _no_store({"error": "internal server error"}, 500)

    message = "device registered" if result.created else "device already registered"
    status_code = 201 if result.created else 200
    return _no_store(
        {
            "message": message,
            "device": result.device.to_dict(),
        },
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
