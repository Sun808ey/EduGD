from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Administrator,
    AdministratorPermission,
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyRevision,
    policy_revision_content_hash,
)
from app.services.policy_assignments import (
    InvalidPolicyAssignmentError,
    PolicyAssignmentConflictError,
    PolicyAssignmentForbiddenError,
    PolicyAssignmentNotFoundError,
    PolicyAssignmentPersistenceError,
    replace_policy_assignment,
)


def _revision(policy: Policy, version: int) -> PolicyRevision:
    payload = {
        "schema_version": 1,
        "blocked_apps": [f"com.example.policy{version}"],
    }
    return PolicyRevision(
        policy=policy,
        version=version,
        payload=payload,
        content_hash=policy_revision_content_hash(payload),
        created_by="migration:policy-assignment-service-test",
    )


def _setup(
    *, permission: bool = True
) -> tuple[Device, Administrator, list[PolicyRevision]]:
    device = Device(device_uuid=uuid4(), android_version="10", api_level=29)
    administrator = Administrator(
        username=f"assignment.admin.{uuid4().hex[:8]}",
        display_name="Assignment Administrator",
        password_verifier="scrypt:test-verifier",
    )
    policy = Policy(policy_uuid=uuid4(), name="Assignment service policy")
    revisions = [_revision(policy, 1), _revision(policy, 2)]
    db.session.add_all([device, administrator, policy, *revisions])
    db.session.flush()
    if permission:
        db.session.add(
            AdministratorPermission(
                administrator_id=administrator.id,
                permission="policy.assign",
                trusted_operator_subject="test:assignment-bootstrap",
                reason="Authorize policy assignment tests",
            )
        )
    db.session.commit()
    return device, administrator, revisions


def test_replacement_is_transactional_idempotent_and_forensic(app: Flask) -> None:
    with app.app_context():
        device, administrator, revisions = _setup()

        first = replace_policy_assignment(
            str(device.device_uuid),
            str(revisions[0].revision_uuid),
            str(administrator.administrator_uuid),
            "Initial approved policy",
        )
        repeated = replace_policy_assignment(
            str(device.device_uuid),
            str(revisions[0].revision_uuid),
            str(administrator.administrator_uuid),
            "Repeated delivery must be idempotent",
        )
        second = replace_policy_assignment(
            str(device.device_uuid),
            str(revisions[1].revision_uuid),
            str(administrator.administrator_uuid),
            "Approved replacement policy",
        )

        assignments = db.session.scalars(
            select(DevicePolicyAssignment)
            .where(DevicePolicyAssignment.device_id == device.id)
            .order_by(DevicePolicyAssignment.id)
        ).all()
        assert first.replaced is False
        assert repeated.assignment.id == first.assignment.id
        assert second.replaced is True
        assert len(assignments) == 2
        assert assignments[0].status == "superseded"
        assert assignments[0].superseded_at is not None
        assert assignments[0].policy_revision_id == revisions[0].id
        assert assignments[1].status == "active"
        assert assignments[1].policy_revision_id == revisions[1].id
        assert assignments[1].assigned_by_administrator_id == administrator.id
        assert assignments[1].trusted_operator_subject is None
        assert assignments[1].reason == "Approved replacement policy"
        assert assignments[0].event_uuid != assignments[1].event_uuid
        assert assignments[0].event_uuid.version == 4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("device", "not-a-uuid"),
        ("revision", "not-a-uuid"),
        ("administrator", "not-a-uuid"),
        ("reason", ""),
        ("reason", "x" * 513),
        ("reason", "line\nbreak"),
    ],
)
def test_assignment_rejects_invalid_input(
    app: Flask,
    field: str,
    value: str,
) -> None:
    with app.app_context():
        device, administrator, revisions = _setup()
        values = {
            "device": str(device.device_uuid),
            "revision": str(revisions[0].revision_uuid),
            "administrator": str(administrator.administrator_uuid),
            "reason": "Approved assignment",
        }
        values[field] = value
        with pytest.raises(InvalidPolicyAssignmentError):
            replace_policy_assignment(
                values["device"],
                values["revision"],
                values["administrator"],
                values["reason"],
            )


def test_assignment_requires_permission_and_active_objects(app: Flask) -> None:
    with app.app_context():
        device, administrator, revisions = _setup(permission=False)
        with pytest.raises(PolicyAssignmentForbiddenError):
            replace_policy_assignment(
                str(device.device_uuid),
                str(revisions[0].revision_uuid),
                str(administrator.administrator_uuid),
                "Unauthorized assignment",
            )

        administrator.status = "disabled"
        administrator.disabled_at = db.func.now()
        db.session.add(
            AdministratorPermission(
                administrator_id=administrator.id,
                permission="policy.assign",
                trusted_operator_subject="test:assignment-bootstrap",
                reason="Test inactive administrator",
            )
        )
        db.session.commit()
        with pytest.raises(PolicyAssignmentForbiddenError):
            replace_policy_assignment(
                str(device.device_uuid),
                str(revisions[0].revision_uuid),
                str(administrator.administrator_uuid),
                "Inactive administrator",
            )


def test_assignment_distinguishes_missing_and_inactive_targets(app: Flask) -> None:
    with app.app_context():
        device, administrator, revisions = _setup()
        with pytest.raises(PolicyAssignmentNotFoundError):
            replace_policy_assignment(
                str(uuid4()),
                str(revisions[0].revision_uuid),
                str(administrator.administrator_uuid),
                "Missing device",
            )

        device.status = "suspended"
        db.session.commit()
        with pytest.raises(PolicyAssignmentConflictError):
            replace_policy_assignment(
                str(device.device_uuid),
                str(revisions[0].revision_uuid),
                str(administrator.administrator_uuid),
                "Inactive device",
            )

        device.status = "active"
        revisions[0].policy.status = "revoked"
        db.session.commit()
        with pytest.raises(PolicyAssignmentNotFoundError):
            replace_policy_assignment(
                str(device.device_uuid),
                str(revisions[0].revision_uuid),
                str(administrator.administrator_uuid),
                "Revoked policy",
            )


def test_assignment_rolls_back_database_failure(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with app.app_context():
        device, administrator, revisions = _setup()

        def fail_commit() -> None:
            db.session.flush()
            raise SQLAlchemyError("forced failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyAssignmentPersistenceError):
            replace_policy_assignment(
                str(device.device_uuid),
                str(revisions[0].revision_uuid),
                str(administrator.administrator_uuid),
                "Rollback verification",
            )

        assert (
            db.session.scalar(select(func.count()).select_from(DevicePolicyAssignment))
            == 0
        )
