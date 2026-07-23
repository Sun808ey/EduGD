from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Policy, PolicyRevision
from app.services.policy_revisions import (
    DuplicatePolicyRevisionError,
    InvalidPolicyRevisionError,
    PolicyNotFoundError,
    PolicyRevisionPersistenceError,
    create_policy_revision,
)


def test_create_policy_revision_allocates_monotonic_versions(app: Flask) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Revision service")
        db.session.add(policy)
        db.session.commit()
        actor_uuid = uuid4()

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
        assert first.revision_uuid.version == 4
        assert first.content_hash != second.content_hash


def test_create_policy_revision_rejects_duplicate_content(app: Flask) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="No duplicate content")
        db.session.add(policy)
        db.session.commit()
        actor_uuid = uuid4()
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
        db.session.add(policy)
        db.session.commit()

        with pytest.raises(InvalidPolicyRevisionError):
            create_policy_revision(
                "invalid" if field == "policy" else str(policy.policy_uuid),
                [],
                "invalid" if field == "actor" else str(uuid4()),
            )


def test_create_policy_revision_rejects_missing_policy(app: Flask) -> None:
    with app.app_context():
        with pytest.raises(PolicyNotFoundError):
            create_policy_revision(str(uuid4()), [], str(uuid4()))


def test_create_policy_revision_rolls_back_database_failure(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Rollback")
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
                str(uuid4()),
            )

        assert db.session.scalar(select(func.count()).select_from(PolicyRevision)) == 0
