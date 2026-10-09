from flask import Blueprint, Response, current_app, request

from app.admin_api import admin_error, admin_json, isoformat_utc
from app.administrator_authorization import (
    administrator_required,
    get_administrator_request_context,
)
from app.models import School
from app.services.school_registration import (
    SchoolAlreadyRegistered,
    SchoolRegistrationError,
    SchoolRegistrationUnavailable,
    get_school,
    register_school,
    update_school,
)

school_bp = Blueprint("schools", __name__)
_SCHOOL_FIELDS = {
    "name",
    "district",
    "school_type",
    "contact_person",
    "official_telephone",
    "official_email",
    "physical_location",
    "authorised_administrator_name",
}
_SCHOOL_FIELDS_WITH_TIMEZONE = _SCHOOL_FIELDS | {"timezone"}


def _school_payload(school: School) -> dict[str, object]:
    return {
        "school_uuid": str(school.school_uuid),
        "name": school.name,
        "district": school.district,
        "school_type": school.school_type,
        "contact_person": school.contact_person,
        "official_telephone": school.official_telephone,
        "official_email": school.official_email,
        "physical_location": school.physical_location,
        "authorised_administrator_name": school.authorised_administrator_name,
        "created_at": isoformat_utc(school.created_at),
        "timezone": school.timezone,
    }


@school_bp.get("/admin/school")
@administrator_required()
def current_school() -> Response:
    try:
        school = get_school()
    except SchoolRegistrationUnavailable:
        return admin_error(
            "school_unavailable", "school is temporarily unavailable", 503
        )
    return admin_json({"school": _school_payload(school) if school else None})


@school_bp.post("/admin/school")
@administrator_required(permission="administrator.manage")
def create_school() -> Response:
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) not in (
        _SCHOOL_FIELDS,
        _SCHOOL_FIELDS_WITH_TIMEZONE,
    ):
        return admin_error("invalid_school", "invalid school registration request", 400)
    payload.setdefault("timezone", "Africa/Kampala")
    if payload["official_email"] == "":
        payload["official_email"] = None
    try:
        school = register_school(
            payload=payload,
            administrator_id=get_administrator_request_context().administrator.id,
        )
    except SchoolAlreadyRegistered:
        return admin_error(
            "school_already_registered", "a school is already registered", 409
        )
    except SchoolRegistrationUnavailable:
        return admin_error(
            "school_unavailable", "school is temporarily unavailable", 503
        )
    except SchoolRegistrationError:
        return admin_error("invalid_school", "invalid school registration request", 400)
    return admin_json({"school": _school_payload(school)}, 201)


@school_bp.patch("/admin/school")
@administrator_required(permission="administrator.manage")
def edit_school() -> Response:
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != _SCHOOL_FIELDS_WITH_TIMEZONE:
        return admin_error("invalid_school", "invalid school profile request", 400)
    if payload["official_email"] == "":
        payload["official_email"] = None
    try:
        school = update_school(
            payload=payload,
            administrator_id=get_administrator_request_context().administrator.id,
        )
    except SchoolRegistrationUnavailable:
        return admin_error("school_unavailable", "school could not be updated", 503)
    except SchoolRegistrationError:
        return admin_error("invalid_school", "invalid school profile request", 400)
    return admin_json({"school": _school_payload(school)})
