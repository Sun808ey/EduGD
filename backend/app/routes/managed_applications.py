from __future__ import annotations

from uuid import UUID

from flask import Blueprint, Response, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.admin_api import admin_error, admin_json
from app.administrator_authorization import administrator_required
from app.device_cryptography import decode_base64url, encode_base64url
from app.extensions import db
from app.models import ManagedApplication, utc_now

managed_application_bp = Blueprint("managed_applications", __name__)


def _serialize(application: ManagedApplication) -> dict[str, object]:
    return {
        "application_uuid": str(application.application_uuid),
        "display_name": application.display_name,
        "package_name": application.package_name,
        "signing_certificate_sha256": (
            encode_base64url(application.signing_certificate_sha256)
            if application.signing_certificate_sha256 is not None
            else None
        ),
        "category": application.category,
        "education_approved": application.education_approved,
        "mandatory_block": application.mandatory_block,
        "status": application.status,
        "created_at": application.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": application.updated_at.isoformat().replace("+00:00", "Z"),
    }


def _parse_payload(payload: object) -> dict[str, object]:
    fields = {
        "display_name",
        "package_name",
        "signing_certificate_sha256",
        "category",
        "education_approved",
        "mandatory_block",
        "status",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("invalid managed application payload")
    digest = payload["signing_certificate_sha256"]
    parsed_digest = None if digest is None else decode_base64url(digest, decoded_length=32)
    if not isinstance(payload["education_approved"], bool) or not isinstance(
        payload["mandatory_block"], bool
    ):
        raise ValueError("invalid managed application flags")
    return {**payload, "signing_certificate_sha256": parsed_digest}


@managed_application_bp.get("/admin/applications")
@administrator_required()
def list_managed_applications() -> Response:
    applications = db.session.execute(
        select(ManagedApplication).order_by(
            ManagedApplication.category, ManagedApplication.display_name
        )
    ).scalars()
    return admin_json({"applications": [_serialize(item) for item in applications]})


@managed_application_bp.post("/admin/applications")
@administrator_required(permission="policy.manage")
def create_managed_application() -> Response:
    try:
        values = _parse_payload(request.get_json(silent=False))
        application = ManagedApplication(**values)
        db.session.add(application)
        db.session.commit()
    except (TypeError, ValueError):
        db.session.rollback()
        return admin_error("invalid_application", "invalid application entry", 400)
    except IntegrityError:
        db.session.rollback()
        return admin_error("application_conflict", "application already exists", 409)
    except SQLAlchemyError:
        db.session.rollback()
        return admin_error("write_unavailable", "applications are temporarily unavailable", 503)
    return admin_json({"application": _serialize(application)}, 201)


@managed_application_bp.patch("/admin/applications/<application_uuid>")
@administrator_required(permission="policy.manage")
def update_managed_application(application_uuid: str) -> Response:
    try:
        parsed_uuid = UUID(application_uuid)
        if parsed_uuid.version != 4 or str(parsed_uuid) != application_uuid:
            raise ValueError
        application = db.session.scalar(
            select(ManagedApplication).where(
                ManagedApplication.application_uuid == parsed_uuid
            )
        )
        if application is None:
            return admin_error("application_not_found", "application not found", 404)
        values = _parse_payload(request.get_json(silent=False))
        for key, value in values.items():
            setattr(application, key, value)
        application.updated_at = utc_now()
        db.session.commit()
    except (TypeError, ValueError):
        db.session.rollback()
        return admin_error("invalid_application", "invalid application entry", 400)
    except IntegrityError:
        db.session.rollback()
        return admin_error("application_conflict", "application already exists", 409)
    except SQLAlchemyError:
        db.session.rollback()
        return admin_error("write_unavailable", "applications are temporarily unavailable", 503)
    return admin_json({"application": _serialize(application)})