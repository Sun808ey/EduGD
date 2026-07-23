from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import delete, select, text

from app.extensions import db
from app.models import Policy, PolicyRevision
from app.services.policy_revisions import create_policy_revision
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

pytestmark = [pytest.mark.postgres, pytest.mark.concurrency]


def test_concurrent_revision_creation_allocates_unique_monotonic_versions(
    postgres_app: Flask,
) -> None:
    approved = validate_postgres_test_environment(require_destructive=True)
    policy_uuid = uuid4()
    actor_uuid = uuid4()
    with postgres_app.app_context():
        with db.engine.connect() as connection:
            validate_connected_postgres_test_environment(
                connection,
                approved,
                require_destructive=True,
            )
        db.session.add(
            Policy(policy_uuid=policy_uuid, name="Concurrent revision policy")
        )
        db.session.commit()
        db.session.remove()

    def create_once(index: int) -> int:
        with postgres_app.app_context():
            try:
                revision = create_policy_revision(
                    str(policy_uuid),
                    [f"com.example.concurrent{index}"],
                    str(actor_uuid),
                )
                return revision.version
            finally:
                db.session.remove()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            versions = sorted(executor.map(create_once, range(2)))

        assert versions == [1, 2]
        with postgres_app.app_context():
            revisions = (
                db.session.execute(
                    select(PolicyRevision)
                    .join(Policy)
                    .where(Policy.policy_uuid == policy_uuid)
                    .order_by(PolicyRevision.version)
                )
                .scalars()
                .all()
            )
            assert [revision.version for revision in revisions] == [1, 2]
            assert len({revision.revision_uuid for revision in revisions}) == 2
            assert len({revision.content_hash for revision in revisions}) == 2
            db.session.remove()
    finally:
        with postgres_app.app_context():
            try:
                db.session.execute(
                    text(
                        "ALTER TABLE policy_revisions "
                        "DISABLE TRIGGER trg_policy_revisions_immutable"
                    )
                )
                policy_id = db.session.scalar(
                    select(Policy.id).where(Policy.policy_uuid == policy_uuid)
                )
                if policy_id is not None:
                    db.session.execute(
                        delete(PolicyRevision).where(
                            PolicyRevision.policy_id == policy_id
                        )
                    )
                db.session.execute(
                    text(
                        "ALTER TABLE policy_revisions "
                        "ENABLE TRIGGER trg_policy_revisions_immutable"
                    )
                )
                if policy_id is not None:
                    db.session.execute(
                        delete(Policy).where(Policy.id == policy_id)
                    )
                db.session.commit()
            except Exception:
                db.session.rollback()
                db.session.execute(
                    text(
                        "ALTER TABLE policy_revisions "
                        "ENABLE TRIGGER trg_policy_revisions_immutable"
                    )
                )
                db.session.commit()
                raise
            finally:
                db.session.remove()
