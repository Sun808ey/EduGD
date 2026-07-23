from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import CheckConstraint, DateTime, Index, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex

from app.extensions import db
from app.models import (
    Device,
    DevicePolicyAssignment,
    Policy,
    PolicyRevision,
    policy_revision_content_hash,
    utc_now,
)


def make_revision(
    policy: Policy,
    version: int,
    blocked_apps: list[str],
) -> PolicyRevision:
    payload = {"schema_version": 1, "blocked_apps": blocked_apps}
    return PolicyRevision(
        policy=policy,
        version=version,
        payload=payload,
        content_hash=policy_revision_content_hash(payload),
        created_by=str(uuid4()),
    )


def test_device_policy_assignment_model_contract() -> None:
    table = DevicePolicyAssignment.__table__

    assert table.name == "device_policy_assignments"
    assert table.c.id.primary_key is True
    assert table.c.device_id.nullable is False
    assert table.c.policy_revision_id.nullable is False
    assert table.c.status.nullable is False
    assert table.c.status.default.arg == "active"
    assert table.c.status.server_default.arg == "active"

    foreign_keys = {
        foreign_key.target_fullname: foreign_key.ondelete
        for foreign_key in table.foreign_keys
    }
    assert foreign_keys == {
        "devices.id": "RESTRICT",
        "policy_revisions.id": "RESTRICT",
    }

    checks = {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "status IN ('active', 'superseded')" in checks
    assert any("superseded_at IS NULL" in check for check in checks)

    assert isinstance(table.c.assigned_at.type, DateTime)
    assert table.c.assigned_at.type.timezone is True
    assert table.c.assigned_at.nullable is False
    assert isinstance(table.c.superseded_at.type, DateTime)
    assert table.c.superseded_at.type.timezone is True
    assert table.c.superseded_at.nullable is True

    active_index = next(
        index
        for index in table.indexes
        if index.name == "uq_device_policy_assignments_active_device"
    )
    assert isinstance(active_index, Index)
    assert active_index.unique is True
    assert tuple(active_index.columns.keys()) == ("device_id",)

    postgresql_index = str(
        CreateIndex(active_index).compile(dialect=postgresql.dialect())
    )
    sqlite_index = str(CreateIndex(active_index).compile(dialect=sqlite.dialect()))
    assert "WHERE status = 'active'" in postgresql_index
    assert "WHERE status = 'active'" in sqlite_index


def test_assignment_replacement_preserves_history(app: Flask) -> None:
    with app.app_context():
        device = Device(
            device_uuid=uuid4(),
            android_version="10",
            api_level=29,
            status="active",
        )
        first_policy = Policy(
            policy_uuid=uuid4(),
            name="Initial policy",
            status="active",
        )
        second_policy = Policy(
            policy_uuid=uuid4(),
            name="Updated policy",
            status="active",
        )
        first_revision = make_revision(first_policy, 1, ["com.facebook.katana"])
        second_revision = make_revision(
            second_policy,
            2,
            ["com.facebook.katana", "com.instagram.android"],
        )
        db.session.add_all(
            [
                device,
                first_policy,
                second_policy,
                first_revision,
                second_revision,
            ]
        )
        db.session.commit()

        first_assignment = DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=first_revision.id,
            status="active",
        )
        db.session.add(first_assignment)
        db.session.commit()

        conflicting_assignment = DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=second_revision.id,
            status="active",
        )
        db.session.add(conflicting_assignment)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        first_assignment = db.session.execute(
            select(DevicePolicyAssignment).where(
                DevicePolicyAssignment.device_id == device.id
            )
        ).scalar_one()
        first_assignment.status = "superseded"
        first_assignment.superseded_at = utc_now()

        replacement_assignment = DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=second_revision.id,
            status="active",
        )
        db.session.add(replacement_assignment)
        db.session.commit()

        assignments = (
            db.session.execute(
                select(DevicePolicyAssignment)
                .where(DevicePolicyAssignment.device_id == device.id)
                .order_by(DevicePolicyAssignment.id)
            )
            .scalars()
            .all()
        )

        assert len(assignments) == 2
        assert assignments[0].status == "superseded"
        assert assignments[0].policy_revision.version == 1
        assert assignments[0].superseded_at is not None
        assert assignments[1].status == "active"
        assert assignments[1].policy_revision.version == 2
        assert assignments[1].superseded_at is None
