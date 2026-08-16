from flask import Blueprint, Response, current_app, jsonify, request

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
from app.models import POLICY_STATUSES
from app.policy_assignment_schemas import (
    PolicyAssignmentRequestError,
    validate_assignment_request,
    validate_clear_request,
)
from app.services.admin_read import (
    AdminReadNotFoundError,
    AdminReadPersistenceError,
    get_policy,
    list_policies,
    list_policy_revisions,
)
from app.services.policy_assignments import (
    InvalidPolicyAssignmentError,
    PolicyAssignmentConflictError,
    PolicyAssignmentNotFoundError,
    PolicyAssignmentPersistenceError,
    clear_policy_assignment,
    replace_policy_assignment,
)

policy_bp = Blueprint("policies", __name__)


@policy_bp.get("/admin/policies")
@administrator_required()
def admin_policies() -> Response:
    try:
        pagination = parse_pagination()
        status = parse_optional_filter("status", POLICY_STATUSES)
        page = list_policies(pagination, status=status)
    except AdminRequestError as error:
        return admin_error(error.code, error.message, error.status_code)
    except AdminReadPersistenceError:
        return admin_error(
            "read_unavailable", "policies are temporarily unavailable", 503
        )
    return admin_json({"policies": page.items, "pagination": page.pagination})


@policy_bp.get("/admin/policies/<policy_uuid>")
@administrator_required()
def admin_policy_detail(policy_uuid: str) -> Response:
    try:
        policy = get_policy(policy_uuid)
    except ValueError:
        return admin_error("invalid_policy_uuid", "policy_uuid must be a UUIDv4", 400)
    except AdminReadNotFoundError:
        return admin_error("policy_not_found", "policy not found", 404)
    except AdminReadPersistenceError:
        return admin_error("read_unavailable", "policy is temporarily unavailable", 503)
    return admin_json({"policy": policy})


@policy_bp.get("/admin/policies/<policy_uuid>/revisions")
@administrator_required()
def admin_policy_revisions(policy_uuid: str) -> Response:
    try:
        pagination = parse_pagination()
        page = list_policy_revisions(policy_uuid, pagination)
    except AdminRequestError as error:
        return admin_error(error.code, error.message, error.status_code)
    except ValueError:
        return admin_error("invalid_policy_uuid", "policy_uuid must be a UUIDv4", 400)
    except AdminReadNotFoundError:
        return admin_error("policy_not_found", "policy not found", 404)
    except AdminReadPersistenceError:
        return admin_error(
            "read_unavailable", "policy revisions are temporarily unavailable", 503
        )
    return admin_json({"revisions": page.items, "pagination": page.pagination})


@policy_bp.post("/admin/devices/<device_uuid>/policy-assignment")
@administrator_required(permission="policy.assign")
def assign_device_policy(device_uuid: str) -> Response:
    request.max_content_length = current_app.config[
        "ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH"
    ]
    try:
        data = validate_assignment_request(request)
        context = get_administrator_request_context()
        result = replace_policy_assignment(
            device_uuid,
            data.policy_revision_uuid,
            str(context.administrator.administrator_uuid),
            data.reason,
        )
    except PolicyAssignmentRequestError as error:
        return _error(
            error.code, "invalid policy assignment request", error.status_code
        )
    except InvalidPolicyAssignmentError:
        return _error("invalid_request", "invalid policy assignment request", 400)
    except PolicyAssignmentNotFoundError:
        return _error("assignment_target_not_found", "assignment target not found", 404)
    except PolicyAssignmentConflictError:
        return _error(
            "assignment_conflict", "policy assignment conflicts with current state", 409
        )
    except PolicyAssignmentPersistenceError:
        return _error(
            "assignment_unavailable",
            "policy assignment is temporarily unavailable",
            503,
        )
    assignment = result.assignment
    return _json_no_store(
        {
            "assignment": {
                "event_uuid": str(assignment.event_uuid),
                "device_uuid": device_uuid,
                "policy_revision_uuid": data.policy_revision_uuid,
                "status": assignment.status,
                "replaced": result.replaced,
            }
        },
        200,
    )


@policy_bp.post("/admin/devices/<device_uuid>/policy-assignment/clear")
@administrator_required(permission="policy.assign")
def clear_device_policy(device_uuid: str) -> Response:
    request.max_content_length = current_app.config[
        "ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH"
    ]
    try:
        reason = validate_clear_request(request)
        context = get_administrator_request_context()
        result = clear_policy_assignment(
            device_uuid,
            str(context.administrator.administrator_uuid),
            reason,
        )
    except PolicyAssignmentRequestError as error:
        return _error(error.code, "invalid policy clear request", error.status_code)
    except InvalidPolicyAssignmentError:
        return _error("invalid_request", "invalid policy clear request", 400)
    except PolicyAssignmentNotFoundError:
        return _error("device_not_found", "device not found", 404)
    except PolicyAssignmentConflictError:
        return _error(
            "assignment_conflict", "policy clear conflicts with current state", 409
        )
    except PolicyAssignmentPersistenceError:
        return _error(
            "assignment_unavailable", "policy clear is temporarily unavailable", 503
        )
    return _json_no_store(
        {
            "clear_intent": {
                "event_uuid": str(result.event.event_uuid),
                "device_uuid": device_uuid,
                "operation": "clear",
            }
        },
        200,
    )


def _error(code: str, message: str, status: int) -> Response:
    return admin_error(code, message, status)


def _json_no_store(payload: dict[str, object], status: int) -> Response:
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response
