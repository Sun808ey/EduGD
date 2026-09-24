"""Immutable policy authoring for authenticated administrators."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import (
    Administrator,
    Policy,
    PolicyRevision,
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
    checked_payload = validate_policy_revision_payload(payload)
    try:
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
    checked_payload = validate_policy_revision_payload(payload)
    try:
        policy = db.session.scalar(
            select(Policy).where(Policy.policy_uuid == policy_uuid).with_for_update()
        )
        administrator = db.session.get(Administrator, administrator_id)
        if policy is None:
            raise PolicyAdministrationNotFound("policy not found")
        if administrator is None or administrator.status != "active":
            raise PolicyAdministrationError("administrator is unavailable")
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
