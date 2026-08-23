from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import delete, select, text

from app.extensions import db
from app.models import (
    Administrator,
    AdministratorPermission,
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyAssignmentChainHead,
    PolicyAssignmentEvent,
    PolicyRevision,
    policy_revision_content_hash,
)
from app.services.policy_assignments import replace_policy_assignment
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

pytestmark = [pytest.mark.postgres, pytest.mark.concurrency]


def test_concurrent_assignment_replacement_preserves_forensic_history(
    postgres_app: Flask,
) -> None:
    approved = validate_postgres_test_environment(require_destructive=True)
    device_uuid = uuid4()
    policy_uuid = uuid4()
    with postgres_app.app_context():
        with db.engine.connect() as connection:
            validate_connected_postgres_test_environment(
                connection,
                approved,
                require_destructive=True,
            )
        device = Device(
            device_uuid=device_uuid,
            android_version="10",
            api_level=29,
        )
        administrator = Administrator(
            username=f"assignment.concurrent.{uuid4().hex[:8]}",
            display_name="Assignment Concurrency Administrator",
            password_verifier="scrypt:test-verifier",
        )
        policy = Policy(policy_uuid=policy_uuid, name="Concurrent assignment policy")
        db.session.add_all([device, administrator, policy])
        db.session.flush()
        permission = AdministratorPermission(
            administrator_id=administrator.id,
            permission="policy.assign",
            trusted_operator_subject="test:postgres-concurrency",
            reason="Authorize concurrent assignment verification",
        )
        revisions: list[PolicyRevision] = []
        for version in (1, 2):
            payload = {
                "schema_version": 1,
                "blocked_apps": [f"com.example.concurrent{version}"],
            }
            revisions.append(
                PolicyRevision(
                    policy_id=policy.id,
                    version=version,
                    payload=payload,
                    content_hash=policy_revision_content_hash(payload),
                    created_by="migration:postgres-assignment-concurrency",
                )
            )
        db.session.add_all([permission, *revisions])
        db.session.commit()
        administrator_uuid = administrator.administrator_uuid
        administrator_id = administrator.id
        device_id = device.id
        policy_id = policy.id
        revision_uuids = [revision.revision_uuid for revision in revisions]
        revision_ids = {revision.id for revision in revisions}
        db.session.remove()

    def assign_once(revision_uuid: object) -> int:
        with postgres_app.app_context():
            try:
                result = replace_policy_assignment(
                    str(device_uuid),
                    str(revision_uuid),
                    str(administrator_uuid),
                    f"Concurrent assignment of {revision_uuid}",
                )
                return result.assignment.id
            finally:
                db.session.remove()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assignment_ids = list(executor.map(assign_once, revision_uuids))

        assert len(set(assignment_ids)) == 2
        with postgres_app.app_context():
            assignments = db.session.scalars(
                select(DevicePolicyAssignment)
                .where(DevicePolicyAssignment.device_id == device_id)
                .order_by(DevicePolicyAssignment.id)
            ).all()
            assert len(assignments) == 2
            assert sum(item.status == "active" for item in assignments) == 1
            assert sum(item.status == "superseded" for item in assignments) == 1
            assert len({item.event_uuid for item in assignments}) == 2
            assert all(
                item.assigned_by_administrator_id == administrator_id
                for item in assignments
            )
            assert all(
                item.reason.startswith("Concurrent assignment") for item in assignments
            )
            assert {item.policy_revision_id for item in assignments} == revision_ids
            db.session.remove()
    finally:
        with postgres_app.app_context():
            try:
                db.session.execute(
                    text(
                        "ALTER TABLE policy_assignment_events "
                        "DISABLE TRIGGER trg_policy_assignment_events_immutable"
                    )
                )
                db.session.execute(
                    delete(PolicyAssignmentEvent).where(
                        PolicyAssignmentEvent.device_id == device_id
                    )
                )
                db.session.execute(
                    delete(PolicyAssignmentChainHead).where(
                        PolicyAssignmentChainHead.device_id == device_id
                    )
                )
                db.session.execute(
                    delete(DevicePolicyAssignment).where(
                        DevicePolicyAssignment.device_id == device_id
                    )
                )
                db.session.execute(
                    text(
                        "ALTER TABLE policy_revisions "
                        "DISABLE TRIGGER trg_policy_revisions_immutable"
                    )
                )
                db.session.execute(
                    delete(PolicyRevision).where(PolicyRevision.policy_id == policy_id)
                )
                db.session.execute(
                    text(
                        "ALTER TABLE policy_revisions "
                        "ENABLE TRIGGER trg_policy_revisions_immutable"
                    )
                )
                db.session.execute(delete(Policy).where(Policy.id == policy_id))
                db.session.execute(
                    delete(AdministratorPermission).where(
                        AdministratorPermission.administrator_id == administrator_id
                    )
                )
                db.session.execute(
                    delete(Administrator).where(Administrator.id == administrator_id)
                )
                db.session.execute(delete(Device).where(Device.id == device_id))
                db.session.commit()
            except Exception:
                db.session.rollback()
                db.session.execute(
                    text(
                        "ALTER TABLE policy_assignment_events "
                        "ENABLE TRIGGER trg_policy_assignment_events_immutable"
                    )
                )
                db.session.execute(
                    text(
                        "ALTER TABLE policy_revisions "
                        "ENABLE TRIGGER trg_policy_revisions_immutable"
                    )
                )
                db.session.commit()
                raise
            finally:
                db.session.execute(
                    text(
                        "ALTER TABLE policy_assignment_events "
                        "ENABLE TRIGGER trg_policy_assignment_events_immutable"
                    )
                )
                db.session.commit()
                db.session.remove()
