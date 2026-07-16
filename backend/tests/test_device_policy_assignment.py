from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import CheckConstraint, DateTime, Index, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex

from app.extensions import db
from app.models import Device, DevicePolicyAssignment, Policy, utc_now


def test_device_policy_assignment_model_contract() -> None:
    table = DevicePolicyAssignment.__table__

    assert table.name == "device_policy_assignments"
    assert table.c.id.primary_key is True
    assert table.c.device_id.nullable is False
    assert table.c.policy_id.nullable is False
    assert table.c.policy_version.nullable is False
    assert table.c.policy_version.default.arg == 1
    assert table.c.policy_version.server_default.arg == "1"
    assert table.c.status.nullable is False
    assert table.c.status.default.arg == "active"
    assert table.c.status.server_default.arg == "active"

    foreign_keys = {
        foreign_key.target_fullname: foreign_key.ondelete
        for foreign_key in table.foreign_keys
    }
    assert foreign_keys == {
        "devices.id": "RESTRICT",
        "policies.id": "RESTRICT",
    }

    checks = {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "policy_version >= 1" in checks
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
            status="active",
        )
        first_policy = Policy(
            policy_uuid=uuid4(),
            name="Initial policy",
            version=1,
            status="active",
            blocked_apps=["com.facebook.katana"],
        )
        second_policy = Policy(
            policy_uuid=uuid4(),
            name="Updated policy",
            version=2,
            status="active",
            blocked_apps=["com.facebook.katana", "com.instagram.android"],
        )
        db.session.add_all([device, first_policy, second_policy])
        db.session.commit()

        first_assignment = DevicePolicyAssignment(
            device_id=device.id,
            policy_id=first_policy.id,
            policy_version=first_policy.version,
            status="active",
        )
        db.session.add(first_assignment)
        db.session.commit()

        conflicting_assignment = DevicePolicyAssignment(
            device_id=device.id,
            policy_id=second_policy.id,
            policy_version=second_policy.version,
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
            policy_id=second_policy.id,
            policy_version=second_policy.version,
            status="active",
        )
        db.session.add(replacement_assignment)
        db.session.commit()

        assignments = db.session.execute(
            select(DevicePolicyAssignment)
            .where(DevicePolicyAssignment.device_id == device.id)
            .order_by(DevicePolicyAssignment.id)
        ).scalars().all()

        assert len(assignments) == 2
        assert assignments[0].status == "superseded"
        assert assignments[0].policy_version == 1
        assert assignments[0].superseded_at is not None
        assert assignments[1].status == "active"
        assert assignments[1].policy_version == 2
        assert assignments[1].superseded_at is None
