from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.device_identity import parse_canonical_uuid4
from app.extensions import db
from app.models import (
    POLICY_REVISION_SCHEMA_VERSION,
    Administrator,
    Policy,
    PolicyRevision,
    policy_revision_content_hash,
    validate_policy_revision_payload,
)


class InvalidPolicyRevisionError(ValueError):
    pass


class PolicyNotFoundError(LookupError):
    pass


class DuplicatePolicyRevisionError(RuntimeError):
    pass


class PolicyRevisionPersistenceError(RuntimeError):
    pass


class PolicyRevisionActorError(PermissionError):
    pass


def create_policy_revision(
    policy_uuid: object,
    blocked_apps: object,
    created_by: object,
) -> PolicyRevision:
    canonical_policy_uuid = _parse_uuid(policy_uuid, "policy_uuid")
    canonical_actor_uuid = _parse_uuid(created_by, "created_by")
    payload = validate_policy_revision_payload(
        {
            "schema_version": POLICY_REVISION_SCHEMA_VERSION,
            "blocked_apps": blocked_apps,
        }
    )
    content_hash = policy_revision_content_hash(payload)

    try:
        administrator = db.session.execute(
            select(Administrator).where(
                Administrator.administrator_uuid == canonical_actor_uuid,
                Administrator.status == "active",
            )
        ).scalar_one_or_none()
        if administrator is None:
            raise PolicyRevisionActorError(
                "created_by must identify an active administrator"
            )

        policy = db.session.execute(
            select(Policy)
            .where(Policy.policy_uuid == canonical_policy_uuid)
            .with_for_update()
        ).scalar_one_or_none()
        if policy is None:
            raise PolicyNotFoundError("policy not found")

        current_version = db.session.scalar(
            select(func.max(PolicyRevision.version)).where(
                PolicyRevision.policy_id == policy.id
            )
        )
        revision = PolicyRevision(
            policy_id=policy.id,
            version=(current_version or 0) + 1,
            payload=payload,
            content_hash=content_hash,
            created_by=str(canonical_actor_uuid),
            created_by_administrator_id=administrator.id,
        )
        db.session.add(revision)
        db.session.commit()
        return revision
    except (PolicyNotFoundError, PolicyRevisionActorError):
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise DuplicatePolicyRevisionError(
            "policy revision version or content already exists"
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise PolicyRevisionPersistenceError(
            "policy revision could not be persisted"
        ) from error


def _parse_uuid(value: object, field: str) -> UUID:
    try:
        return parse_canonical_uuid4(value)
    except ValueError as error:
        raise InvalidPolicyRevisionError(f"invalid {field}") from error


__all__ = [
    "DuplicatePolicyRevisionError",
    "InvalidPolicyRevisionError",
    "PolicyNotFoundError",
    "PolicyRevisionPersistenceError",
    "PolicyRevisionActorError",
    "create_policy_revision",
]
