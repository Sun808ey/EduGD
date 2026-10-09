from __future__ import annotations

from uuid import UUID

from flask import Blueprint, Response, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.admin_api import admin_error, admin_json
from app.administrator_authorization import administrator_required
from app.device_cryptography import decode_base64url, encode_base64url
from app.extensions import db
from app.models import ManagedApplication, ManagedDomain, utc_now

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


def _parse_payload(
    payload: object, *, require_verified_identity: bool = True
) -> dict[str, object]:
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
    if require_verified_identity and not isinstance(digest, str):
        raise ValueError("verified signing certificate digest is required")
    parsed_digest = (
        None if digest is None else decode_base64url(digest, decoded_length=32)
    )
    if not isinstance(payload["education_approved"], bool) or not isinstance(
        payload["mandatory_block"], bool
    ):
        raise ValueError("invalid managed application flags")
    return {**payload, "signing_certificate_sha256": parsed_digest}


def _serialize_domain(domain: ManagedDomain) -> dict[str, object]:
    return {
        "domain_uuid": str(domain.domain_uuid),
        "domain": domain.domain,
        "category": domain.category,
        "status": domain.status,
        "created_at": domain.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": domain.updated_at.isoformat().replace("+00:00", "Z"),
    }


def _parse_domain_payload(payload: object) -> dict[str, object]:
    fields = {"domain", "category", "status"}
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("invalid managed domain payload")
    domain = payload["domain"]
    category = payload["category"]
    status = payload["status"]
    if (
        not isinstance(domain, str)
        or not isinstance(category, str)
        or not isinstance(status, str)
    ):
        raise ValueError("invalid managed domain payload")
    return {
        "domain": domain,
        "category": category.strip().lower(),
        "status": status,
    }


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
        return admin_error(
            "write_unavailable", "applications are temporarily unavailable", 503
        )
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
        return admin_error(
            "write_unavailable", "applications are temporarily unavailable", 503
        )
    return admin_json({"application": _serialize(application)})


@managed_application_bp.get("/admin/domains")
@administrator_required()
def list_managed_domains() -> Response:
    domains = db.session.execute(
        select(ManagedDomain)
        .where(ManagedDomain.status == "enabled")
        .order_by(ManagedDomain.category, ManagedDomain.domain)
    ).scalars()
    return admin_json({"domains": [_serialize_domain(item) for item in domains]})


@managed_application_bp.post("/admin/domains")
@administrator_required(permission="policy.manage")
def create_managed_domain() -> Response:
    try:
        domain = ManagedDomain(**_parse_domain_payload(request.get_json(silent=False)))
        db.session.add(domain)
        db.session.commit()
    except (TypeError, ValueError):
        db.session.rollback()
        return admin_error("invalid_domain", "invalid domain entry", 400)
    except IntegrityError:
        db.session.rollback()
        return admin_error("domain_conflict", "domain already exists", 409)
    except SQLAlchemyError:
        db.session.rollback()
        return admin_error(
            "write_unavailable", "domains are temporarily unavailable", 503
        )
    return admin_json({"domain": _serialize_domain(domain)}, 201)


@managed_application_bp.patch("/admin/domains/<domain_uuid>")
@administrator_required(permission="policy.manage")
def update_managed_domain(domain_uuid: str) -> Response:
    try:
        parsed_uuid = UUID(domain_uuid)
        if parsed_uuid.version != 4 or str(parsed_uuid) != domain_uuid:
            raise ValueError
        domain = db.session.scalar(
            select(ManagedDomain).where(ManagedDomain.domain_uuid == parsed_uuid)
        )
        if domain is None:
            return admin_error("domain_not_found", "domain not found", 404)
        for key, value in _parse_domain_payload(request.get_json(silent=False)).items():
            setattr(domain, key, value)
        domain.updated_at = utc_now()
        db.session.commit()
    except (TypeError, ValueError):
        db.session.rollback()
        return admin_error("invalid_domain", "invalid domain entry", 400)
    except IntegrityError:
        db.session.rollback()
        return admin_error("domain_conflict", "domain already exists", 409)
    except SQLAlchemyError:
        db.session.rollback()
        return admin_error(
            "write_unavailable", "domains are temporarily unavailable", 503
        )
    return admin_json({"domain": _serialize_domain(domain)})
