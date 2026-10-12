import csv
from io import StringIO

from flask import Blueprint, Response, request

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
    list_policy_changes,
)
from app.services.violation_reports import (
    ViolationReportPersistenceError,
    all_violations,
    build_filters,
    list_violations,
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


@logs_bp.get("/admin/policy-changes")
@administrator_required()
def policy_changes() -> Response:
    try:
        page = list_policy_changes(parse_pagination())
    except AdminRequestError as error:
        return admin_error(error.code, error.message, error.status_code)
    except AdminReadPersistenceError:
        return admin_error(
            "read_unavailable", "policy changes are temporarily unavailable", 503
        )
    return admin_json({"policy_changes": page.items, "pagination": page.pagination})


@logs_bp.get("/admin/reports/violations")
@administrator_required()
def violation_report() -> Response:
    try:
        filters = build_filters(
            device_uuid=request.args.get("device_uuid"),
            class_name=request.args.get("class_name"),
            from_date=request.args.get("from"),
            to_date=request.args.get("to"),
        )
        items, pagination = list_violations(parse_pagination(), filters)
    except (AdminRequestError, ValueError) as error:
        if isinstance(error, AdminRequestError):
            return admin_error(error.code, error.message, error.status_code)
        return admin_error("invalid_report_filter", str(error), 400)
    except ViolationReportPersistenceError:
        return admin_error(
            "read_unavailable", "violation reports are temporarily unavailable", 503
        )
    return admin_json({"violations": items, "pagination": pagination})


@logs_bp.get("/admin/reports/violations.csv")
@administrator_required()
def violation_report_csv() -> Response:
    try:
        filters = build_filters(
            device_uuid=request.args.get("device_uuid"),
            class_name=request.args.get("class_name"),
            from_date=request.args.get("from"),
            to_date=request.args.get("to"),
        )
        rows = all_violations(filters)
    except ValueError as error:
        return admin_error("invalid_report_filter", str(error), 400)
    except ViolationReportPersistenceError:
        return admin_error(
            "read_unavailable", "violation reports are temporarily unavailable", 503
        )
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "event_uuid",
            "device_uuid",
            "asset_number",
            "class_name",
            "occurred_at",
            "violation_type",
            "event_code",
            "outcome",
            "rule_id",
            "policy_name",
            "policy_version",
            "details",
            "sequence",
            "event_hash",
        ),
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, "details": str(row["details"])})
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = (
        "attachment; filename=edugd-violations.csv"
    )
    response.headers["Cache-Control"] = "no-store"
    return response
