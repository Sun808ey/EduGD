from datetime import timedelta
from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Administrator, Policy, PolicyRevision, utc_now
from app.services.policy_revisions import (
    DuplicatePolicyRevisionError,
    InvalidPolicyRevisionError,
    PolicyNotFoundError,
    PolicyRevisionActorError,
    PolicyRevisionPersistenceError,
    create_policy_revision,
)


def _actor(*, status: str = "active") -> Administrator:
    lifecycle: dict[str, object] = {}
    if status == "disabled":
        lifecycle["disabled_at"] = utc_now()
    elif status == "locked":
        lifecycle.update(
            failed_attempts=5,
            lock_expires_at=utc_now() + timedelta(minutes=15),
        )
    administrator = Administrator(
        username=f"policy.admin.{uuid4().hex[:8]}",
        display_name="Policy Administrator",
        password_verifier="scrypt:test-verifier",
        status=status,
        **lifecycle,
    )
    db.session.add(administrator)
    db.session.flush()
    return administrator


def test_create_policy_revision_allocates_monotonic_versions(app: Flask) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Revision service")
        actor = _actor()
        db.session.add(policy)
        db.session.commit()
        actor_uuid = actor.administrator_uuid

        first = create_policy_revision(
            str(policy.policy_uuid),
            ["com.example.first"],
            str(actor_uuid),
        )
        second = create_policy_revision(
            str(policy.policy_uuid),
            ["com.example.second"],
            str(actor_uuid),
        )

        assert (first.version, second.version) == (1, 2)
        assert first.created_by == str(actor_uuid)
        assert first.created_by_administrator_id == actor.id
        assert first.revision_uuid.version == 4
        assert first.content_hash != second.content_hash


def test_create_policy_revision_rejects_duplicate_content(app: Flask) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="No duplicate content")
        actor = _actor()
        db.session.add(policy)
        db.session.commit()
        actor_uuid = actor.administrator_uuid
        create_policy_revision(
            str(policy.policy_uuid),
            ["com.example.same"],
            str(actor_uuid),
        )

        with pytest.raises(DuplicatePolicyRevisionError):
            create_policy_revision(
                str(policy.policy_uuid),
                ["com.example.same"],
                str(actor_uuid),
            )

        assert db.session.scalar(select(func.count()).select_from(PolicyRevision)) == 1


@pytest.mark.parametrize("field", ["policy", "actor"])
def test_create_policy_revision_rejects_invalid_identity(
    app: Flask,
    field: str,
) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Validated identity")
        actor = _actor()
        db.session.add(policy)
        db.session.commit()

        with pytest.raises(InvalidPolicyRevisionError):
            create_policy_revision(
                "invalid" if field == "policy" else str(policy.policy_uuid),
                [],
                "invalid" if field == "actor" else str(actor.administrator_uuid),
            )


def test_create_policy_revision_rejects_missing_policy(app: Flask) -> None:
    with app.app_context():
        actor = _actor()
        db.session.commit()
        with pytest.raises(PolicyNotFoundError):
            create_policy_revision(str(uuid4()), [], str(actor.administrator_uuid))


@pytest.mark.parametrize("status", ["disabled", "locked"])
def test_create_policy_revision_rejects_unavailable_actor(
    app: Flask,
    status: str,
) -> None:
    with app.app_context():
        actor = _actor(status=status)
        policy = Policy(policy_uuid=uuid4(), name="Actor enforcement")
        db.session.add(policy)
        db.session.commit()

        with pytest.raises(PolicyRevisionActorError):
            create_policy_revision(
                str(policy.policy_uuid),
                [],
                str(actor.administrator_uuid),
            )


def test_create_policy_revision_rejects_unknown_actor(app: Flask) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Unknown actor")
        db.session.add(policy)
        db.session.commit()

        with pytest.raises(PolicyRevisionActorError):
            create_policy_revision(
                str(policy.policy_uuid),
                [],
                str(uuid4()),
            )


def test_create_policy_revision_rolls_back_database_failure(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Rollback")
        actor = _actor()
        db.session.add(policy)
        db.session.commit()

        def fail_commit() -> None:
            db.session.flush()
            raise SQLAlchemyError("forced failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyRevisionPersistenceError):
            create_policy_revision(
                str(policy.policy_uuid),
                [],
                str(actor.administrator_uuid),
            )

        assert db.session.scalar(select(func.count()).select_from(PolicyRevision)) == 0
