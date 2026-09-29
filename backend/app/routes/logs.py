from flask import Blueprint, Response

from app.admin_api import (
    AdminRequestError,
    admin_error,
    admin_json,
    parse_optional_filter,
    parse_pagination,
)
from app.administrator_authorization import administrator_required
from app.services.admin_read import (
    AUDIT_EVENT_TYPES,
    AdminReadPersistenceError,
    list_audit_events,
)

logs_bp = Blueprint("logs", __name__)


@logs_bp.get("/admin/audit-events")
@administrator_required()
def audit_events() -> Response:
    try:
        pagination = parse_pagination()
        event_type = parse_optional_filter("event_type", AUDIT_EVENT_TYPES)
        page = list_audit_events(pagination, event_type=event_type)
    except AdminRequestError as error:
        return admin_error(error.code, error.message, error.status_code)
    except AdminReadPersistenceError:
        return admin_error(
            "read_unavailable", "audit events are temporarily unavailable", 503
        )
    return admin_json({"audit_events": page.items, "pagination": page.pagination})
