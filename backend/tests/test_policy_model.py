from typing import Any
from uuid import uuid4

import pytest
from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Index,
    UniqueConstraint,
    Uuid,
    insert,
    inspect,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from app.extensions import db
from app.models import POLICY_STATUSES, Policy

VALID_BLOCKED_APPS = [
    "com.facebook.katana",
    "com.instagram.android",
]


def test_policy_model_contract() -> None:
    table = Policy.__table__

    assert table.name == "policies"
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False

    assert isinstance(table.c.policy_uuid.type, Uuid)
    assert table.c.policy_uuid.type.as_uuid is True
    assert table.c.policy_uuid.nullable is False

    unique_constraints = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("policy_uuid",) in unique_constraints

    indexes = {
        tuple(index.columns.keys())
        for index in table.indexes
        if isinstance(index, Index)
    }
    assert ("policy_uuid",) in indexes

    assert table.c.name.nullable is False
    assert table.c.version.nullable is False
    assert table.c.version.default.arg == 1
    assert table.c.version.server_default.arg == "1"
    assert table.c.status.nullable is False
    assert table.c.status.default.arg == "active"
    assert table.c.status.server_default.arg == "active"

    assert isinstance(table.c.blocked_apps.type, JSON)
    assert table.c.blocked_apps.nullable is False
    assert table.c.blocked_apps.server_default.arg == "[]"

    check_constraints = {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    check_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "version >= 1" in check_constraints
    assert (
        "status IN ('draft', 'active', 'inactive', 'revoked')"
        in check_constraints
    )
    assert "ck_policies_blocked_apps" in check_constraint_names

    timestamp_columns = (table.c.created_at, table.c.updated_at)
    assert all(isinstance(column.type, DateTime) for column in timestamp_columns)
    assert all(column.type.timezone is True for column in timestamp_columns)
    assert all(column.nullable is False for column in timestamp_columns)
    assert table.c.updated_at.onupdate is not None

    postgresql_ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    sqlite_ddl = str(CreateTable(table).compile(dialect=sqlite.dialect()))
    assert "UUID" in postgresql_ddl
    assert "JSON" in postgresql_ddl
    assert "ck_policies_blocked_apps" in postgresql_ddl
    assert "CHAR(32)" in sqlite_ddl
    assert "JSON" in sqlite_ddl
    assert "ck_policies_blocked_apps" not in sqlite_ddl


def test_policy_accepts_android_package_identifiers() -> None:
    policy = Policy(
        policy_uuid=uuid4(),
        name="Classroom policy",
        version=1,
        status="active",
        blocked_apps=VALID_BLOCKED_APPS,
    )

    assert policy.blocked_apps == VALID_BLOCKED_APPS
    assert policy.blocked_apps is not VALID_BLOCKED_APPS


def test_valid_in_place_mutation_persists_and_preserves_order(app: Flask) -> None:
    with app.app_context():
        policy = Policy(
            policy_uuid=uuid4(),
            name="Mutable classroom policy",
            blocked_apps=["com.instagram.android"],
        )
        db.session.add(policy)
        db.session.commit()

        policy.blocked_apps.insert(0, "com.facebook.katana")
        policy.blocked_apps.extend(["org.example.learning"])
        db.session.commit()
        policy_id = policy.id
        db.session.expire_all()

        stored = db.session.get(Policy, policy_id)
        assert stored is not None
        assert stored.blocked_apps == [
            "com.facebook.katana",
            "com.instagram.android",
            "org.example.learning",
        ]


@pytest.mark.parametrize(
    "operation",
    [
        "append_display_name",
        "extend_duplicate",
        "insert_invalid",
        "replace_invalid",
        "replace_slice_duplicate",
        "in_place_add_invalid",
        "in_place_multiply_duplicate",
    ],
)
def test_invalid_in_place_mutation_is_rejected_atomically(operation: str) -> None:
    policy = Policy(
        policy_uuid=uuid4(),
        name="Atomic blocked-app validation",
        blocked_apps=VALID_BLOCKED_APPS,
    )
    original = list(policy.blocked_apps)

    with pytest.raises(ValueError, match="Android package identifiers"):
        if operation == "append_display_name":
            policy.blocked_apps.append("facebook")
        elif operation == "extend_duplicate":
            policy.blocked_apps.extend(["org.example.learning", original[0]])
        elif operation == "insert_invalid":
            policy.blocked_apps.insert(0, "com.invalid-package")
        elif operation == "replace_invalid":
            policy.blocked_apps[0] = "instagram"
        elif operation == "replace_slice_duplicate":
            policy.blocked_apps[:] = [original[0], original[0]]
        elif operation == "in_place_add_invalid":
            policy.blocked_apps += ["com..invalid"]
        else:
            policy.blocked_apps *= 2

    assert policy.blocked_apps == original


@pytest.mark.parametrize("status", sorted(POLICY_STATUSES))
def test_policy_accepts_approved_statuses(status: str) -> None:
    policy = Policy(
        policy_uuid=uuid4(),
        name="Approved lifecycle policy",
        status=status,
        blocked_apps=[],
    )

    assert policy.status == status


@pytest.mark.parametrize("status", ["published", "", None, 1])
def test_policy_rejects_invalid_status_in_model(status: object) -> None:
    with pytest.raises(ValueError, match="invalid policy status"):
        Policy(
            policy_uuid=uuid4(),
            name="Invalid lifecycle policy",
            status=status,
            blocked_apps=[],
        )


def test_database_rejects_invalid_policy_status(app: Flask) -> None:
    with app.app_context():
        with pytest.raises(IntegrityError):
            db.session.execute(
                insert(Policy).values(
                    policy_uuid=uuid4(),
                    name="Invalid database policy",
                    status="published",
                    blocked_apps=[],
                )
            )
            db.session.commit()
        db.session.rollback()


def test_policy_status_migration_downgrades_and_upgrades_on_sqlite(
    app: Flask,
) -> None:
    with app.app_context():
        downgrade(revision="e7c4a9b2d6f1")
        downgraded_checks = {
            constraint["name"]
            for constraint in inspect(db.engine).get_check_constraints("policies")
        }

        upgrade(revision="head")
        upgraded_checks = {
            constraint["name"]
            for constraint in inspect(db.engine).get_check_constraints("policies")
        }

    assert "ck_policies_status" not in downgraded_checks
    assert "ck_policies_status" in upgraded_checks


@pytest.mark.parametrize(
    "blocked_apps",
    [
        ["facebook", "instagram"],
        ["com.valid.package", "instagram"],
        ["com.invalid-package"],
        ["com..invalid"],
        [10],
        "com.facebook.katana",
        ["com.facebook.katana", "com.facebook.katana"],
    ],
)
def test_policy_rejects_invalid_blocked_apps(blocked_apps: Any) -> None:
    with pytest.raises(ValueError, match="Android package identifiers"):
        Policy(
            policy_uuid=uuid4(),
            name="Invalid policy",
            version=1,
            status="active",
            blocked_apps=blocked_apps,
        )
