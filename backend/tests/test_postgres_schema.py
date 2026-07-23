from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, insert, inspect, select, text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import DateTime

from app.models import (
    Device,
    DeviceCredential,
    DevicePolicyAssignment,
    DeviceRequestNonce,
    Policy,
    PolicyRevision,
    policy_revision_content_hash,
    utc_now,
)

pytestmark = pytest.mark.postgres


def _device() -> Device:
    return Device(device_uuid=uuid4(), android_version="10", api_level=29)


def _policy(**overrides: object) -> Policy:
    values = {
        "policy_uuid": uuid4(),
        "name": "Test policy",
    }
    values.update(overrides)
    return Policy(**values)


def _revision(
    policy: Policy,
    *,
    version: int = 1,
    blocked_apps: object = None,
) -> PolicyRevision:
    apps = ["org.example.learning"] if blocked_apps is None else blocked_apps
    payload = {"schema_version": 1, "blocked_apps": apps}
    return PolicyRevision(
        policy=policy,
        version=version,
        payload=payload,
        content_hash=policy_revision_content_hash(payload),
        created_by=str(uuid4()),
    )


def _expect_integrity_error(session: Session, model: object) -> None:
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(model)
            session.flush()


def test_existing_schema_metadata_and_constraints(
    postgres_session: Session,
) -> None:
    inspector = inspect(postgres_session.connection())
    expected_tables = {
        "devices",
        "policies",
        "policy_revisions",
        "device_policy_assignments",
        "device_registration_events",
        "enrollment_tokens",
        "device_credentials",
        "device_request_nonces",
        "device_enrollment_events",
        "administrators",
        "administrator_permissions",
        "administrator_sessions",
        "administrator_authentication_events",
    }
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
    revision_uniques = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints("policy_revisions")
    }
    assert revision_uniques["uq_policy_revisions_revision_uuid"] == ["revision_uuid"]
    assert revision_uniques["uq_policy_revisions_policy_version"] == [
        "policy_id",
        "version",
    ]
    assert revision_uniques["uq_policy_revisions_policy_content_hash"] == [
        "policy_id",
        "content_hash",
    ]

    foreign_keys = inspector.get_foreign_keys("device_policy_assignments")
    foreign_key_targets = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            foreign_key["options"].get("ondelete"),
        )
        for foreign_key in foreign_keys
    }
    assert foreign_key_targets[("device_id",)] == ("devices", "RESTRICT")
    assert foreign_key_targets[("policy_revision_id",)] == (
        "policy_revisions",
        "RESTRICT",
    )
    revision_foreign_key = inspector.get_foreign_keys("policy_revisions")
    assert len(revision_foreign_key) == 1
    assert revision_foreign_key[0]["referred_table"] == "policies"
    assert revision_foreign_key[0]["options"].get("ondelete") == "RESTRICT"

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
    revision_columns = {
        column["name"]: column for column in inspector.get_columns("policy_revisions")
    }
    assert isinstance(device_columns["device_uuid"]["type"], POSTGRES_UUID)
    assert isinstance(policy_columns["policy_uuid"]["type"], POSTGRES_UUID)
    assert isinstance(revision_columns["revision_uuid"]["type"], POSTGRES_UUID)
    assert isinstance(revision_columns["payload"]["type"], JSON)
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
        "policy_revisions": {
            name for name, column in revision_columns.items() if column["nullable"]
        },
    }
    assert nullable_columns == {
        "devices": {"last_sync_at"},
        "policies": set(),
        "device_policy_assignments": {"superseded_at"},
        "policy_revisions": set(),
    }
    for columns, timestamp_names in (
        (
            device_columns,
            {"registered_at", "last_sync_at", "created_at", "updated_at"},
        ),
        (policy_columns, {"created_at", "updated_at"}),
        (assignment_columns, {"assigned_at", "superseded_at"}),
        (revision_columns, {"created_at"}),
    ):
        assert all(
            cast(DateTime, columns[name]["type"]).timezone for name in timestamp_names
        )

    policy_checks = {
        constraint["name"] for constraint in inspector.get_check_constraints("policies")
    }
    device_checks = {
        constraint["name"] for constraint in inspector.get_check_constraints("devices")
    }
    assert device_checks == {
        "ck_devices_android_api_match",
        "ck_devices_api_level_supported",
        "ck_devices_status",
    }
    assignment_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("device_policy_assignments")
    }
    assert policy_checks == {"ck_policies_status"}
    assert assignment_checks == {
        "ck_device_policy_assignments_status",
        "ck_device_policy_assignments_status_timestamp",
    }
    revision_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("policy_revisions")
    }
    assert revision_checks == {
        "ck_policy_revisions_content_hash_length",
        "ck_policy_revisions_payload",
        "ck_policy_revisions_version_positive",
    }

    registration_foreign_keys = inspector.get_foreign_keys("device_registration_events")
    assert len(registration_foreign_keys) == 1
    assert registration_foreign_keys[0]["constrained_columns"] == ["device_id"]
    assert registration_foreign_keys[0]["referred_table"] == "devices"
    assert registration_foreign_keys[0]["options"].get("ondelete") == "RESTRICT"

    registration_columns = {
        column["name"]
        for column in inspector.get_columns("device_registration_events")
        if column["nullable"]
    }
    assert registration_columns == set()
    registration_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("device_registration_events")
    }
    assert registration_checks == {
        "ck_device_registration_events_reported_api_level",
        "ck_device_registration_events_stored_api_level",
        "ck_device_registration_events_type",
    }


def test_enrollment_authentication_schema_constraints(
    postgres_session: Session,
) -> None:
    inspector = inspect(postgres_session.connection())

    expected_checks = {
        "enrollment_tokens": {
            "ck_enrollment_tokens_consumption_state",
            "ck_enrollment_tokens_expiry",
            "ck_enrollment_tokens_failed_attempts",
            "ck_enrollment_tokens_pepper_version",
            "ck_enrollment_tokens_revocation_state",
            "ck_enrollment_tokens_status",
            "ck_enrollment_tokens_verifier_length",
        },
        "device_credentials": {
            "ck_device_credentials_algorithm",
            "ck_device_credentials_fingerprint_length",
            "ck_device_credentials_lifecycle",
            "ck_device_credentials_public_key_length",
            "ck_device_credentials_status",
        },
        "device_request_nonces": {
            "ck_device_request_nonces_expiry",
            "ck_device_request_nonces_hash_length",
        },
        "device_enrollment_events": {
            "ck_device_enrollment_events_category",
            "ck_device_enrollment_events_fingerprint_length",
        },
    }
    for table_name, constraint_names in expected_checks.items():
        assert {
            constraint["name"]
            for constraint in inspector.get_check_constraints(table_name)
        } == constraint_names

    for table_name in expected_checks:
        assert {
            foreign_key["options"].get("ondelete")
            for foreign_key in inspector.get_foreign_keys(table_name)
        } <= {"RESTRICT"}

    credential_indexes = {
        index["name"]: index for index in inspector.get_indexes("device_credentials")
    }
    active_index = credential_indexes["uq_device_credentials_active_device"]
    assert active_index["unique"] is True
    assert active_index["column_names"] == ["device_id"]
    active_predicate = str(active_index["dialect_options"]["postgresql_where"])
    assert "status" in active_predicate
    assert "'active'" in active_predicate

    for table_name, uuid_column in (
        ("enrollment_tokens", "token_uuid"),
        ("device_credentials", "credential_uuid"),
        ("device_enrollment_events", "event_uuid"),
    ):
        columns = {
            column["name"]: column for column in inspector.get_columns(table_name)
        }
        assert isinstance(columns[uuid_column]["type"], POSTGRES_UUID)


def test_existing_device_enrollment_classification_on_postgres(
    postgres_session: Session,
) -> None:
    device = _device()
    postgres_session.add(device)
    postgres_session.flush()

    assert device.enrollment_state == "legacy_pending"

    credential = DeviceCredential(
        device_id=device.id,
        algorithm="RSA_2048_SHA256",
        public_key_der=b"public-key-der",
        public_key_fingerprint=b"f" * 32,
    )
    postgres_session.add(credential)
    postgres_session.flush()
    postgres_session.expire(device, ["credentials"])

    assert device.enrollment_state == "enrolled"


def test_postgres_rejects_a_second_active_credential_for_one_device(
    postgres_session: Session,
) -> None:
    device = _device()
    postgres_session.add(device)
    postgres_session.flush()
    postgres_session.add(
        DeviceCredential(
            device_id=device.id,
            algorithm="RSA_2048_SHA256",
            public_key_der=b"first-public-key",
            public_key_fingerprint=b"a" * 32,
        )
    )
    postgres_session.flush()

    _expect_integrity_error(
        postgres_session,
        DeviceCredential(
            device_id=device.id,
            algorithm="RSA_2048_SHA256",
            public_key_der=b"second-public-key",
            public_key_fingerprint=b"b" * 32,
        ),
    )


def test_postgres_rejects_a_replayed_nonce_for_one_credential(
    postgres_session: Session,
) -> None:
    device = _device()
    postgres_session.add(device)
    postgres_session.flush()
    credential = DeviceCredential(
        device_id=device.id,
        algorithm="RSA_2048_SHA256",
        public_key_der=b"nonce-test-public-key",
        public_key_fingerprint=b"n" * 32,
    )
    postgres_session.add(credential)
    postgres_session.flush()
    now = utc_now()
    postgres_session.add(
        DeviceRequestNonce(
            credential_id=credential.id,
            nonce_hash=b"r" * 32,
            observed_at=now,
            expires_at=now + timedelta(minutes=10),
        )
    )
    postgres_session.flush()

    _expect_integrity_error(
        postgres_session,
        DeviceRequestNonce(
            credential_id=credential.id,
            nonce_hash=b"r" * 32,
            observed_at=now,
            expires_at=now + timedelta(minutes=10),
        ),
    )


def test_administrator_authentication_schema_constraints(
    postgres_session: Session,
) -> None:
    inspector = inspect(postgres_session.connection())
    expected_checks = {
        "administrators": {
            "ck_administrators_display_name_bounded",
            "ck_administrators_failed_attempts",
            "ck_administrators_lifecycle",
            "ck_administrators_password_verifier",
            "ck_administrators_status",
            "ck_administrators_username_bounded",
        },
        "administrator_permissions": {
            "ck_administrator_permissions_grant_actor",
            "ck_administrator_permissions_operator_bounded",
            "ck_administrator_permissions_permission",
            "ck_administrator_permissions_reason_bounded",
        },
        "administrator_sessions": {
            "ck_administrator_sessions_expiry",
            "ck_administrator_sessions_jti_digest_length",
            "ck_administrator_sessions_revocation_metadata_bounded",
            "ck_administrator_sessions_revocation_state",
            "ck_administrator_sessions_source_pseudonym_length",
        },
        "administrator_authentication_events": {
            "ck_administrator_authentication_events_actor",
            "ck_administrator_authentication_events_category",
            "ck_administrator_authentication_events_failure_bounded",
            "ck_administrator_authentication_events_metadata_bounded",
            "ck_administrator_authentication_events_source_pseudonym_length",
        },
    }
    for table_name, constraint_names in expected_checks.items():
        assert {
            constraint["name"]
            for constraint in inspector.get_check_constraints(table_name)
        } == constraint_names

    for table_name in (
        "administrator_permissions",
        "administrator_sessions",
        "administrator_authentication_events",
    ):
        assert {
            foreign_key["options"].get("ondelete")
            for foreign_key in inspector.get_foreign_keys(table_name)
        } == {"RESTRICT"}

    administrator_uniques = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints("administrators")
    }
    assert administrator_uniques["uq_administrators_uuid"] == ["administrator_uuid"]
    assert administrator_uniques["uq_administrators_username"] == ["username"]

    session_uniques = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints("administrator_sessions")
    }
    assert session_uniques["uq_administrator_sessions_jti_digest"] == ["jti_digest"]

    for table_name, uuid_column in (
        ("administrators", "administrator_uuid"),
        ("administrator_authentication_events", "event_uuid"),
    ):
        columns = {
            column["name"]: column for column in inspector.get_columns(table_name)
        }
        assert isinstance(columns[uuid_column]["type"], POSTGRES_UUID)


def test_uuid_json_primary_keys_uniqueness_and_timestamps(
    postgres_session: Session,
) -> None:
    device_uuid = uuid4()
    policy_uuid = uuid4()
    device = Device(device_uuid=device_uuid, android_version="10", api_level=29)
    policy = _policy(policy_uuid=policy_uuid)
    postgres_session.add_all([device, policy])
    postgres_session.flush()
    revision = _revision(policy)
    postgres_session.add(revision)
    postgres_session.flush()
    assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=revision.id,
    )
    postgres_session.add(assignment)
    postgres_session.flush()

    assert isinstance(device.id, int)
    assert isinstance(policy.id, int)
    stored_device = postgres_session.get(Device, device.id)
    stored_policy = postgres_session.get(Policy, policy.id)
    assert stored_device is not None
    assert stored_policy is not None
    assert stored_device.device_uuid == device_uuid
    assert stored_policy.policy_uuid == policy_uuid
    assert revision.payload["blocked_apps"] == ["org.example.learning"]
    assert revision.revision_uuid.version == 4
    assert len(revision.content_hash) == 32
    assert isinstance(stored_policy.policy_uuid, UUID)
    timestamp_values = (
        device.registered_at,
        device.created_at,
        device.updated_at,
        stored_policy.created_at,
        stored_policy.updated_at,
        revision.created_at,
        assignment.assigned_at,
    )
    assert all(value.tzinfo is not None for value in timestamp_values)
    assert stored_policy.created_at.utcoffset() == UTC.utcoffset(datetime.now(UTC))

    _expect_integrity_error(
        postgres_session,
        Device(device_uuid=device_uuid, android_version="10", api_level=29),
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
                    android_version="10",
                    api_level=29,
                )
            )


def test_not_null_foreign_keys_and_restrict_delete(
    postgres_session: Session,
) -> None:
    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(
                insert(Device).values(
                    device_uuid=uuid4(),
                    android_version=None,
                    api_level=29,
                )
            )
    _expect_integrity_error(
        postgres_session,
        DevicePolicyAssignment(device_id=-1, policy_revision_id=-1),
    )

    device = _device()
    policy = _policy()
    postgres_session.add_all([device, policy])
    postgres_session.flush()
    revision = _revision(policy)
    postgres_session.add(revision)
    postgres_session.flush()
    assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=revision.id,
    )
    postgres_session.add(assignment)
    postgres_session.flush()

    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(delete(Device).where(Device.id == device.id))
    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(delete(Policy).where(Policy.id == policy.id))


def test_existing_check_constraints(postgres_session: Session) -> None:
    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(
                insert(Device).values(
                    device_uuid=uuid4(),
                    android_version="10",
                    api_level=29,
                    status="invalid",
                )
            )
    for android_version, api_level in (("10", 28), ("11", 30)):
        with pytest.raises(IntegrityError):
            with postgres_session.begin_nested():
                postgres_session.execute(
                    insert(Device).values(
                        device_uuid=uuid4(),
                        android_version=android_version,
                        api_level=api_level,
                        status="active",
                    )
                )
    policy = _policy()
    postgres_session.add(policy)
    postgres_session.flush()
    _expect_integrity_error(
        postgres_session,
        PolicyRevision(
            policy_id=policy.id,
            version=0,
            payload={"schema_version": 1, "blocked_apps": []},
            content_hash=policy_revision_content_hash(
                {"schema_version": 1, "blocked_apps": []}
            ),
            created_by=str(uuid4()),
        ),
    )
    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(
                insert(Policy).values(
                    policy_uuid=uuid4(),
                    name="Invalid status policy",
                    status="published",
                )
            )
    device = _device()
    revision = _revision(policy)
    postgres_session.add_all([device, revision])
    postgres_session.flush()

    invalid_assignments = [
        DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=revision.id,
            status="invalid",
        ),
        DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=revision.id,
            status="active",
            superseded_at=datetime.now(UTC),
        ),
        DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=revision.id,
            status="superseded",
            superseded_at=None,
        ),
    ]
    for assignment in invalid_assignments:
        _expect_integrity_error(postgres_session, assignment)


@pytest.mark.parametrize(
    "blocked_apps",
    [
        {"package": "com.facebook.katana"},
        ["facebook"],
        ["com.invalid-package"],
        ["com.facebook.katana", "com.facebook.katana"],
        ["com.facebook.katana", 10],
        [None],
    ],
)
def test_postgres_rejects_invalid_policy_revision_json(
    postgres_session: Session,
    blocked_apps: object,
) -> None:
    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(
                insert(PolicyRevision).values(
                    revision_uuid=uuid4(),
                    policy_id=postgres_session.scalar(
                        insert(Policy)
                        .values(policy_uuid=uuid4(), name="JSON policy")
                        .returning(Policy.id)
                    ),
                    version=1,
                    payload={
                        "schema_version": 1,
                        "blocked_apps": blocked_apps,
                    },
                    content_hash=b"x" * 32,
                    created_by=str(uuid4()),
                )
            )


def test_postgres_preserves_valid_policy_revision_order(
    postgres_session: Session,
) -> None:
    expected = [
        "org.example.learning",
        "com.facebook.katana",
        "com.instagram.android",
    ]
    policy = _policy(name="Ordered blocked-app policy")
    revision = _revision(policy, blocked_apps=expected)
    postgres_session.add_all([policy, revision])
    postgres_session.flush()

    stored = postgres_session.get(PolicyRevision, revision.id)
    assert stored is not None
    assert stored.payload["blocked_apps"] == expected


def test_postgres_rejects_direct_policy_revision_update_and_delete(
    postgres_session: Session,
) -> None:
    policy = _policy()
    revision = _revision(policy)
    postgres_session.add_all([policy, revision])
    postgres_session.flush()

    for statement in (
        text("UPDATE policy_revisions SET created_by = :actor WHERE id = :revision_id"),
        text("DELETE FROM policy_revisions WHERE id = :revision_id"),
    ):
        with pytest.raises(DBAPIError):
            with postgres_session.begin_nested():
                postgres_session.execute(
                    statement,
                    {
                        "actor": str(uuid4()),
                        "revision_id": revision.id,
                    },
                )

    assert postgres_session.get(PolicyRevision, revision.id) is revision


def test_postgres_rejects_invalid_hash_and_duplicate_revision_evidence(
    postgres_session: Session,
) -> None:
    policy = _policy()
    revision = _revision(policy)
    postgres_session.add_all([policy, revision])
    postgres_session.flush()

    with pytest.raises(IntegrityError):
        with postgres_session.begin_nested():
            postgres_session.execute(
                insert(PolicyRevision).values(
                    revision_uuid=uuid4(),
                    policy_id=policy.id,
                    version=2,
                    payload={
                        "schema_version": 1,
                        "blocked_apps": ["com.example.invalidhash"],
                    },
                    content_hash=b"short",
                    created_by=str(uuid4()),
                )
            )

    _expect_integrity_error(
        postgres_session,
        PolicyRevision(
            policy_id=policy.id,
            version=2,
            payload=revision.payload,
            content_hash=revision.content_hash,
            created_by=str(uuid4()),
        ),
    )


def test_postgres_assignment_reconstructs_exact_historical_revision(
    postgres_session: Session,
) -> None:
    device = _device()
    policy = _policy()
    assigned_revision = _revision(
        policy,
        version=5,
        blocked_apps=["com.example.historical"],
    )
    newer_revision = _revision(
        policy,
        version=6,
        blocked_apps=["com.example.current"],
    )
    postgres_session.add_all(
        [device, policy, assigned_revision, newer_revision]
    )
    postgres_session.flush()
    assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=assigned_revision.id,
    )
    postgres_session.add(assignment)
    postgres_session.flush()

    stored = postgres_session.execute(
        select(PolicyRevision)
        .join(DevicePolicyAssignment)
        .where(DevicePolicyAssignment.id == assignment.id)
    ).scalar_one()
    assert stored.version == 5
    assert stored.payload["blocked_apps"] == ["com.example.historical"]


def test_partial_unique_index_allows_only_one_active_assignment(
    postgres_session: Session,
) -> None:
    device = _device()
    first_policy = _policy(name="First")
    second_policy = _policy(name="Second")
    postgres_session.add_all([device, first_policy, second_policy])
    postgres_session.flush()
    first_revision = _revision(first_policy)
    second_revision = _revision(second_policy)
    postgres_session.add_all([first_revision, second_revision])
    postgres_session.flush()
    first_assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=first_revision.id,
    )
    postgres_session.add(first_assignment)
    postgres_session.flush()

    _expect_integrity_error(
        postgres_session,
        DevicePolicyAssignment(
            device_id=device.id,
            policy_revision_id=second_revision.id,
        ),
    )

    first_assignment.status = "superseded"
    first_assignment.superseded_at = datetime.now(UTC)
    postgres_session.flush()
    replacement = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=second_revision.id,
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
