"""Immutable policy authoring for authenticated administrators."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import (
    Administrator,
    DevicePolicyAssignment,
    ManagedApplication,
    Policy,
    PolicyRevision,
    School,
    policy_revision_content_hash,
    validate_policy_revision_payload,
)


class PolicyAdministrationError(RuntimeError):
    pass


class PolicyAdministrationNotFound(PolicyAdministrationError):
    pass


class PolicyAdministrationConflict(PolicyAdministrationError):
    pass


def create_policy(*, name: object, payload: object, administrator_id: int) -> Policy:
    checked_name = _name(name)
    try:
        checked_payload = validate_policy_revision_payload(
            _materialize_policy_payload(payload)
        )
        _ensure_policy_code_unique(checked_payload)
        administrator = db.session.get(Administrator, administrator_id)
        if administrator is None or administrator.status != "active":
            raise PolicyAdministrationError("administrator is unavailable")
        policy = Policy(policy_uuid=uuid4(), name=checked_name, status="draft")
        db.session.add(policy)
        db.session.flush()
        _add_revision(policy, checked_payload, administrator)
        db.session.commit()
        return policy
    except PolicyAdministrationError:
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise PolicyAdministrationConflict(
            "policy conflicts with existing state"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise PolicyAdministrationError("policy could not be persisted") from error


def add_revision(
    *, policy_uuid: UUID, payload: object, administrator_id: int
) -> PolicyRevision:
    try:
        checked_payload = validate_policy_revision_payload(
            _materialize_policy_payload(payload)
        )
        policy = db.session.scalar(
            select(Policy).where(Policy.policy_uuid == policy_uuid).with_for_update()
        )
        administrator = db.session.get(Administrator, administrator_id)
        if policy is None:
            raise PolicyAdministrationNotFound("policy not found")
        if administrator is None or administrator.status != "active":
            raise PolicyAdministrationError("administrator is unavailable")
        _ensure_required_applications_remain(policy, checked_payload)
        revision = _add_revision(policy, checked_payload, administrator)
        db.session.commit()
        return revision
    except PolicyAdministrationError:
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise PolicyAdministrationConflict(
            "policy revision conflicts with existing state"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise PolicyAdministrationError(
            "policy revision could not be persisted"
        ) from error


def set_lifecycle(*, policy_uuid: UUID, status: object) -> Policy:
    if status not in {"active", "inactive", "revoked"}:
        raise ValueError("invalid lifecycle status")
    try:
        policy = db.session.scalar(
            select(Policy).where(Policy.policy_uuid == policy_uuid).with_for_update()
        )
        if policy is None:
            raise PolicyAdministrationNotFound("policy not found")
        policy.status = status
        db.session.commit()
        return policy
    except PolicyAdministrationError:
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        db.session.rollback()
        raise PolicyAdministrationError(
            "policy lifecycle could not be persisted"
        ) from error


def _add_revision(
    policy: Policy, payload: dict[str, object], administrator: Administrator
) -> PolicyRevision:
    current = (
        db.session.scalar(
            select(func.max(PolicyRevision.version)).where(
                PolicyRevision.policy_id == policy.id
            )
        )
        or 0
    )
    revision = PolicyRevision(
        policy_id=policy.id,
        version=current + 1,
        payload=payload,
        content_hash=policy_revision_content_hash(payload),
        created_by=str(administrator.administrator_uuid),
        created_by_administrator_id=administrator.id,
    )
    db.session.add(revision)
    return revision


def _name(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= 255
        or not value.isprintable()
    ):
        raise ValueError("invalid policy name")
    return value.strip()


def _materialize_device_use_school_name(payload: object) -> object:
    """Derive the displayed organisation name from the registered school.

    The administrator only controls whether the name is shown. They must not
    be able to substitute arbitrary organisation text into a device policy.
    Legacy payloads without ``device_use`` remain byte-for-byte compatible.
    """
    if not isinstance(payload, dict) or "device_use" not in payload:
        return payload
    raw_device_use = payload["device_use"]
    if not isinstance(raw_device_use, dict):
        return payload
    device_use = dict(raw_device_use)
    if device_use.get("display_school_name") is True:
        school = db.session.scalar(select(School).where(School.singleton_key == "1"))
        device_use["school_name"] = school.name if school is not None else None
    else:
        device_use["school_name"] = None
    return {**payload, "device_use": device_use}


def _materialize_policy_payload(payload: object) -> object:
    materialized = _materialize_device_use_school_name(payload)
    if not isinstance(materialized, dict):
        return materialized
    result = materialized
    if "approved_applications" in result:
        raw_applications = result["approved_applications"]
        if not isinstance(raw_applications, list) or not raw_applications:
            raise ValueError("at least one approved application is required")
        canonical: list[dict[str, object]] = []
        seen_uuids: set[UUID] = set()
        seen_packages: set[str] = set()
        allowed_types = {
            "learning_application",
            "digital_textbook",
            "pdf_reader",
            "calculator",
            "approved_browser",
            "accessibility_application",
            "other_approved_application",
        }
        for raw in raw_applications:
            if not isinstance(raw, dict):
                raise ValueError("invalid approved application")
            required_keys = {
                "application_uuid",
                "application_type",
                "required",
                "allow_in_kiosk",
            }
            if not required_keys.issubset(raw) or set(raw) - required_keys - {
                "display_name",
                "package_name",
            }:
                raise ValueError("invalid approved application")
            try:
                application_uuid = UUID(str(raw["application_uuid"]))
            except (AttributeError, ValueError):
                raise ValueError("invalid approved application UUID") from None
            if (
                application_uuid.version != 4
                or str(application_uuid) != raw["application_uuid"]
            ):
                raise ValueError("invalid approved application UUID")
            if application_uuid in seen_uuids:
                raise ValueError("duplicate approved application")
            if (
                raw["application_type"] not in allowed_types
                or not isinstance(raw["required"], bool)
                or not isinstance(raw["allow_in_kiosk"], bool)
            ):
                raise ValueError("invalid approved application flags")
            application = db.session.scalar(
                select(ManagedApplication).where(
                    ManagedApplication.application_uuid == application_uuid
                )
            )
            if (
                application is None
                or application.status != "enabled"
                or not application.education_approved
                or application.mandatory_block
            ):
                raise ValueError("application is not approved for policy use")
            if application.package_name in seen_packages:
                raise ValueError("duplicate approved application package")
            seen_uuids.add(application_uuid)
            seen_packages.add(application.package_name)
            canonical.append(
                {
                    "application_uuid": str(application.application_uuid),
                    "display_name": application.display_name,
                    "package_name": application.package_name,
                    "application_type": raw["application_type"],
                    "required": raw["required"],
                    "allow_in_kiosk": raw["allow_in_kiosk"],
                }
            )
        result = {**result, "approved_applications": canonical}
    if "application_controls" in result:
        raw_controls = result["application_controls"]
        application_control_keys = {
            "allow_installation_of_other_applications",
            "allow_installation_from_unknown_sources",
            "allow_uninstall_of_approved_applications",
            "allow_disable_of_approved_applications",
            "allow_google_play_store",
            "allow_file_sharing_applications",
        }
        if (
            not isinstance(raw_controls, dict)
            or set(raw_controls) != application_control_keys
            or any(
                not isinstance(raw_controls[key], bool)
                for key in application_control_keys
            )
        ):
            raise ValueError("invalid application controls")
        file_sharing_packages = db.session.scalars(
            select(ManagedApplication.package_name).where(
                ManagedApplication.category == "file_sharing"
            )
        ).all()
        result = {
            **result,
            "application_controls": {
                **raw_controls,
                "file_sharing_packages": sorted(set(file_sharing_packages)),
            },
        }
    return result


def _ensure_policy_code_unique(payload: dict[str, object]) -> None:
    code = payload.get("policy_code")
    if not isinstance(code, str):
        return
    for revision in db.session.scalars(select(PolicyRevision)).all():
        if revision.payload.get("policy_code") == code:
            raise PolicyAdministrationConflict("policy code already exists")


def _ensure_required_applications_remain(
    policy: Policy, payload: dict[str, object]
) -> None:
    new_applications = payload.get("approved_applications", [])
    if not isinstance(new_applications, list):
        return
    new_packages = {
        str(item["package_name"])
        for item in new_applications
        if isinstance(item, dict) and item.get("required") is True
    }
    assigned_revisions = db.session.scalars(
        select(PolicyRevision)
        .join(
            DevicePolicyAssignment,
            DevicePolicyAssignment.policy_revision_id == PolicyRevision.id,
        )
        .where(
            PolicyRevision.policy_id == policy.id,
            DevicePolicyAssignment.status == "active",
        )
    ).all()
    for revision in assigned_revisions:
        previous = revision.payload.get("approved_applications")
        if not isinstance(previous, list):
            continue
        previous_required = {
            str(item["package_name"])
            for item in previous
            if isinstance(item, dict) and item.get("required") is True
        }
        if previous_required - new_packages:
            raise PolicyAdministrationConflict(
                "required application cannot be removed while assigned to active devices"
            )
