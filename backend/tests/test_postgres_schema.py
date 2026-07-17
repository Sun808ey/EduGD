from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, insert, inspect, select
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Device, DevicePolicyAssignment, Policy

pytestmark = pytest.mark.postgres


def _device() -> Device:
    return Device(device_uuid=uuid4(), android_version="test-only")


def _policy(**overrides) -> Policy:
    values = {
        "policy_uuid": uuid4(),
        "name": "Test policy",
        "version": 1,
        "blocked_apps": ["org.example.learning"],
    }
    values.update(overrides)
    return Policy(**values)


def _expect_integrity_error(session: Session, model) -> None:
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(model)
            session.flush()


def test_existing_schema_metadata_and_constraints(
    postgres_session: Session,
) -> None:
    inspector = inspect(postgres_session.connection())
    expected_tables = {"devices", "policies", "device_policy_assignments"}
    assert expected_tables.issubset(set(inspector.get_table_names()))

    for table_name in expected_tables:
        primary_key = inspector.get_pk_constraint(table_name)
        assert primary_key["constrained_columns"] == ["id"]

    device_uniques = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints("devices")
    }
    policy_uniques = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints("policies")
    }
    assert device_uniques["uq_devices_device_uuid"] == ["device_uuid"]
    assert policy_uniques["uq_policies_policy_uuid"] == ["policy_uuid"]

    foreign_keys = inspector.get_foreign_keys("device_policy_assignments")
    foreign_key_targets = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            foreign_key["options"].get("ondelete"),
        )
        for foreign_key in foreign_keys
    }
    assert foreign_key_targets[("device_id",)] == ("devices", "RESTRICT")
    assert foreign_key_targets[("policy_id",)] == ("policies", "RESTRICT")

    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("device_policy_assignments")
    }
    active_index = indexes["uq_device_policy_assignments_active_device"]
    assert active_index["unique"] is True
    assert active_index["column_names"] == ["device_id"]
    active_predicate = str(active_index["dialect_options"]["postgresql_where"])
    assert "status" in active_predicate
    assert "'active'" in active_predicate

    device_columns = {
        column["name"]: column for column in inspector.get_columns("devices")
    }
    policy_columns = {
        column["name"]: column for column in inspector.get_columns("policies")
    }
    assignment_columns = {
        column["name"]: column
        for column in inspector.get_columns("device_policy_assignments")
    }
    assert isinstance(device_columns["device_uuid"]["type"], POSTGRES_UUID)
    assert isinstance(policy_columns["policy_uuid"]["type"], POSTGRES_UUID)
    assert isinstance(policy_columns["blocked_apps"]["type"], JSON)
    nullable_columns = {
        "devices": {
            name for name, column in device_columns.items() if column["nullable"]
        },
        "policies": {
            name for name, column in policy_columns.items() if column["nullable"]
        },
        "device_policy_assignments": {
            name for name, column in assignment_columns.items() if column["nullable"]
        },
    }
    assert nullable_columns == {
        "devices": {"last_sync_at"},
        "policies": set(),
        "device_policy_assignments": {"superseded_at"},
    }
    for columns, timestamp_names in (
        (
            device_columns,
            {"registered_at", "last_sync_at", "created_at", "updated_at"},
        ),
        (policy_columns, {"created_at", "updated_at"}),
        (assignment_columns, {"assigned_at", "superseded_at"}),
    ):
        assert all(columns[name]["type"].timezone for name in timestamp_names)

    policy_checks = {
        constraint["name"] for constraint in inspector.get_check_constraints("policies")
    }
    assignment_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("device_policy_assignments")
    }
    assert policy_checks == {"ck_policies_version_positive"}
    assert assignment_checks == {
        "ck_device_policy_assignments_status",
        "ck_device_policy_assignments_status_timestamp",
        "ck_device_policy_assignments_version_positive",
    }


def test_uuid_json_primary_keys_uniqueness_and_timestamps(
    postgres_session: Session,
) -> None:
    device_uuid = uuid4()
    policy_uuid = uuid4()
    device = Device(device_uuid=device_uuid, android_version="test-only")
    policy = _policy(policy_uuid=policy_uuid)
    postgres_session.add_all([device, policy])
    postgres_session.flush()
    assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_id=policy.id,
        policy_version=policy.version,
    )
    postgres_session.add(assignment)
    postgres_session.flush()

    assert isinstance(device.id, int)
    assert isinstance(policy.id, int)
    assert postgres_session.get(Device, device.id).device_uuid == device_uuid
    stored_policy = postgres_session.get(Policy, policy.id)
    assert stored_policy.policy_uuid == policy_uuid
    assert stored_policy.blocked_apps == ["org.example.learning"]
    assert isinstance(stored_policy.policy_uuid, UUID)
    timestamp_values = (
        device.registered_at,
        device.created_at,
        device.updated_at,
        stored_policy.created_at,
        stored_policy.updated_at,
        assignment.assigned_at,
    )
    assert all(value.tzinfo is not None for value in timestamp_values)
    assert stored_policy.created_at.utcoffset() == UTC.utcoffset(datetime.now(UTC))

    _expect_integrity_error(
        postgres_session,
        Device(device_uuid=device_uuid, android_version="duplicate"),
    )
    _expect_integrity_error(
        postgres_session,
        _policy(policy_uuid=policy_uuid),
    )
    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(
                insert(Device).values(
                    id=device.id,
                    device_uuid=uuid4(),
                    android_version="duplicate-primary-key",
                )
            )


def test_not_null_foreign_keys_and_restrict_delete(
    postgres_session: Session,
) -> None:
    _expect_integrity_error(
        postgres_session,
        Device(device_uuid=uuid4(), android_version=None),
    )
    _expect_integrity_error(
        postgres_session,
        DevicePolicyAssignment(device_id=-1, policy_id=-1),
    )

    device = _device()
    policy = _policy()
    postgres_session.add_all([device, policy])
    postgres_session.flush()
    assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_id=policy.id,
        policy_version=policy.version,
    )
    postgres_session.add(assignment)
    postgres_session.flush()

    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(delete(Device).where(Device.id == device.id))


def test_existing_check_constraints(postgres_session: Session) -> None:
    _expect_integrity_error(postgres_session, _policy(version=0))
    device = _device()
    policy = _policy()
    postgres_session.add_all([device, policy])
    postgres_session.flush()

    invalid_assignments = [
        DevicePolicyAssignment(
            device_id=device.id,
            policy_id=policy.id,
            policy_version=0,
        ),
        DevicePolicyAssignment(
            device_id=device.id,
            policy_id=policy.id,
            status="invalid",
        ),
        DevicePolicyAssignment(
            device_id=device.id,
            policy_id=policy.id,
            status="active",
            superseded_at=datetime.now(UTC),
        ),
        DevicePolicyAssignment(
            device_id=device.id,
            policy_id=policy.id,
            status="superseded",
            superseded_at=None,
        ),
    ]
    for assignment in invalid_assignments:
        _expect_integrity_error(postgres_session, assignment)


def test_partial_unique_index_allows_only_one_active_assignment(
    postgres_session: Session,
) -> None:
    device = _device()
    first_policy = _policy(name="First")
    second_policy = _policy(name="Second")
    postgres_session.add_all([device, first_policy, second_policy])
    postgres_session.flush()
    first_assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_id=first_policy.id,
    )
    postgres_session.add(first_assignment)
    postgres_session.flush()

    _expect_integrity_error(
        postgres_session,
        DevicePolicyAssignment(
            device_id=device.id,
            policy_id=second_policy.id,
        ),
    )

    first_assignment.status = "superseded"
    first_assignment.superseded_at = datetime.now(UTC)
    postgres_session.flush()
    replacement = DevicePolicyAssignment(
        device_id=device.id,
        policy_id=second_policy.id,
    )
    postgres_session.add(replacement)
    postgres_session.flush()
    assert (
        postgres_session.scalar(
            select(DevicePolicyAssignment).where(
                DevicePolicyAssignment.id == replacement.id
            )
        )
        is replacement
    )
