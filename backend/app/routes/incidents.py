from __future__ import annotations

from flask import Blueprint, Response, current_app, request

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
from app.device_identity import parse_canonical_uuid4
from app.extensions import limiter
from app.models import INCIDENT_STATUSES, INCIDENT_TYPES
from app.services.incidents import (
    IncidentConflictError,
    IncidentNotFoundError,
    IncidentPersistenceError,
    IncidentValidationError,
    create_incident,
    list_incidents,
    update_incident,
)

incident_bp = Blueprint("incidents", __name__)


@incident_bp.get("/admin/incidents")
@administrator_required()
def admin_incidents() -> Response:
    try:
        page = list_incidents(
            parse_pagination(),
            status=parse_optional_filter("status", INCIDENT_STATUSES),
            incident_type=parse_optional_filter("incident_type", INCIDENT_TYPES),
        )
    except AdminRequestError as error:
        return admin_error(error.code, error.message, error.status_code)
    except IncidentPersistenceError:
        return admin_error(
            "read_unavailable", "incidents are temporarily unavailable", 503
        )
    return admin_json({"incidents": page.items, "pagination": page.pagination})


@incident_bp.get("/admin/devices/<device_uuid>/incidents")
@administrator_required()
def admin_device_incidents(device_uuid: str) -> Response:
    try:
        parsed = parse_canonical_uuid4(device_uuid)
        page = list_incidents(parse_pagination(), device_uuid=parsed)
    except (ValueError, AdminRequestError) as error:
        if isinstance(error, AdminRequestError):
            return admin_error(error.code, error.message, error.status_code)
        return admin_error("invalid_device_uuid", "device_uuid must be a UUIDv4", 400)
    except IncidentPersistenceError:
        return admin_error(
            "read_unavailable", "device incidents are temporarily unavailable", 503
        )
    return admin_json({"incidents": page.items, "pagination": page.pagination})


@incident_bp.post("/admin/incidents")
@administrator_required(permission="policy.manage")
@limiter.limit("30 per minute")
def create_admin_incident() -> Response:
    return admin_error(
        "manual_incidents_disabled",
        "manual incident entry has been replaced by DPC-synchronised violations",
        410,
    )
    # Kept below as historical implementation context; no administrator
    # request can reach it after the explicit return above.
    request.max_content_length = current_app.config[
        "ADMIN_POLICY_MUTATION_MAX_CONTENT_LENGTH"
    ]
    payload = request.get_json(silent=True)
    fields = {
        "device_uuid",
        "incident_type",
        "description",
        "reported_by",
        "responsible_person",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        return admin_error("invalid_incident", "invalid incident request", 400)
    try:
        device_uuid = payload["device_uuid"]
        parsed_device_uuid = (
            parse_canonical_uuid4(device_uuid)
            if isinstance(device_uuid, str) and device_uuid
            else None
        )
        row = create_incident(
            device_uuid=parsed_device_uuid,
            incident_type=payload["incident_type"],
            description=payload["description"],
            reported_by=payload["reported_by"],
            responsible_person=payload["responsible_person"],
            administrator=get_administrator_request_context().administrator,
        )
    except (ValueError, TypeError, IncidentValidationError):
        return admin_error("invalid_incident", "invalid incident request", 400)
    except IncidentNotFoundError:
        return admin_error("device_not_found", "device not found", 404)
    except IncidentConflictError:
        return admin_error("incident_conflict", "incident could not be recorded", 409)
    except IncidentPersistenceError:
        return admin_error("write_unavailable", "incident could not be recorded", 503)
    return admin_json({"incident": row}, 201)


@incident_bp.patch("/admin/incidents/<incident_uuid>")
@administrator_required(permission="policy.manage")
def update_admin_incident(incident_uuid: str) -> Response:
    return admin_error(
        "manual_incidents_disabled",
        "manual incident updates have been replaced by DPC-synchronised violations",
        410,
    )
    payload = request.get_json(silent=True)
    fields = {"status", "action_taken", "responsible_person"}
    if not isinstance(payload, dict) or set(payload) != fields:
        return admin_error("invalid_incident", "invalid incident update request", 400)
    try:
        row = update_incident(
            parse_canonical_uuid4(incident_uuid),
            status=payload["status"],
            action_taken=payload["action_taken"],
            responsible_person=payload["responsible_person"],
            administrator=get_administrator_request_context().administrator,
        )
    except (ValueError, TypeError, IncidentValidationError):
        return admin_error("invalid_incident", "invalid incident update request", 400)
    except IncidentNotFoundError:
        return admin_error("incident_not_found", "incident not found", 404)
    except IncidentConflictError as error:
        return admin_error("incident_conflict", str(error), 409)
    except IncidentPersistenceError:
        return admin_error("write_unavailable", "incident could not be updated", 503)
    return admin_json({"incident": row})
