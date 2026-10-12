from __future__ import annotations

from flask import Blueprint, Response

from app.admin_api import (
    AdminRequestError,
    admin_error,
    admin_json,
    parse_optional_filter,
    parse_pagination,
)
from app.administrator_authorization import (
    administrator_required,
)
from app.device_identity import parse_canonical_uuid4
from app.extensions import limiter
from app.models import INCIDENT_STATUSES, INCIDENT_TYPES
from app.services.incidents import (
    IncidentPersistenceError,
    list_incidents,
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


@incident_bp.patch("/admin/incidents/<incident_uuid>")
@administrator_required(permission="policy.manage")
def update_admin_incident(incident_uuid: str) -> Response:
    return admin_error(
        "manual_incidents_disabled",
        "manual incident updates have been replaced by DPC-synchronised violations",
        410,
    )
