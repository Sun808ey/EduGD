from typing import cast
from uuid import uuid4

import pytest
from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Index,
    LargeBinary,
    UniqueConstraint,
    Uuid,
    insert,
    inspect,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from app.extensions import db
from app.models import (
    POLICY_STATUSES,
    Policy,
    PolicyRevision,
    PolicyRevisionImmutableError,
    canonical_policy_revision_bytes,
    policy_revision_content_hash,
)

VALID_PAYLOAD = {
    "schema_version": 1,
    "blocked_apps": [
        "com.facebook.katana",
        "com.instagram.android",
    ],
}


def _revision(policy: Policy, *, version: int = 1) -> PolicyRevision:
    return PolicyRevision(
        policy=policy,
        version=version,
        payload=VALID_PAYLOAD,
        content_hash=policy_revision_content_hash(VALID_PAYLOAD),
        created_by=str(uuid4()),
    )


def test_policy_model_is_stable_identity_and_lifecycle() -> None:
    table = Policy.__table__

    assert set(table.c.keys()) == {
        "id",
        "policy_uuid",
        "name",
        "status",
        "created_at",
        "updated_at",
    }
    assert table.c.id.primary_key is True
    assert isinstance(table.c.policy_uuid.type, Uuid)
    assert table.c.policy_uuid.type.as_uuid is True
    assert table.c.policy_uuid.nullable is False
    assert ("policy_uuid",) in {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("policy_uuid",) in {
        tuple(index.columns.keys())
        for index in table.indexes
        if isinstance(index, Index)
    }
    assert "status IN ('draft', 'active', 'inactive', 'revoked')" in {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.updated_at.onupdate is not None


def test_policy_revision_model_contract() -> None:
    table = PolicyRevision.__table__

    assert table.name == "policy_revisions"
    assert table.c.id.primary_key is True
    assert isinstance(table.c.revision_uuid.type, Uuid)
    assert table.c.revision_uuid.type.as_uuid is True
    assert table.c.policy_id.nullable is False
    assert isinstance(table.c.payload.type, JSON)
    assert isinstance(table.c.content_hash.type, LargeBinary)
    assert table.c.content_hash.type.length == 32
    assert table.c.created_by.nullable is False
    assert table.c.created_by_administrator_id.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.created_at.type.timezone is True

    assert {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    } >= {
        ("revision_uuid",),
        ("policy_id", "version"),
        ("policy_id", "content_hash"),
    }
    assert {
        foreign_key.target_fullname: foreign_key.ondelete
        for foreign_key in table.foreign_keys
    } == {
        "administrators.id": "RESTRICT",
        "policies.id": "RESTRICT",
    }
    assert {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    } >= {
        "ck_policy_revisions_version_positive",
        "ck_policy_revisions_content_hash_length",
        "ck_policy_revisions_payload",
        "ck_policy_revisions_actor_provenance",
    }

    postgres_ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    sqlite_ddl = str(CreateTable(table).compile(dialect=sqlite.dialect()))
    assert "ck_policy_revisions_payload" in postgres_ddl
    assert "ck_policy_revisions_payload" not in sqlite_ddl


def test_canonical_policy_revision_hash_is_deterministic() -> None:
    differently_ordered = {
        "blocked_apps": VALID_PAYLOAD["blocked_apps"],
        "schema_version": 1,
    }

    assert canonical_policy_revision_bytes(VALID_PAYLOAD) == (
        b'{"blocked_apps":["com.facebook.katana",'
        b'"com.instagram.android"],"schema_version":1}'
    )
    assert policy_revision_content_hash(VALID_PAYLOAD) == (
        policy_revision_content_hash(differently_ordered)
    )
    assert len(policy_revision_content_hash(VALID_PAYLOAD)) == 32


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"schema_version": 1},
        {"schema_version": 2, "blocked_apps": []},
        {"schema_version": 1, "blocked_apps": [], "extra": True},
        {"schema_version": 1, "blocked_apps": ["facebook"]},
        {
            "schema_version": 1,
            "blocked_apps": ["com.example.app", "com.example.app"],
        },
    ],
)
def test_policy_revision_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError):
        PolicyRevision(
            policy_id=1,
            version=1,
            payload=payload,
            content_hash=b"x" * 32,
            created_by=str(uuid4()),
        )


def test_policy_revision_payload_is_copied() -> None:
    source = {
        "schema_version": 1,
        "blocked_apps": ["com.example.learning"],
    }
    revision = PolicyRevision(
        policy_id=1,
        version=1,
        payload=source,
        content_hash=policy_revision_content_hash(source),
        created_by=str(uuid4()),
    )
    cast(list[str], source["blocked_apps"]).append("com.example.changed")

    assert revision.payload == {
        "schema_version": 1,
        "blocked_apps": ["com.example.learning"],
    }

    exposed = revision.payload
    cast(list[str], exposed["blocked_apps"]).append("com.example.changed")
    assert revision.payload == {
        "schema_version": 1,
        "blocked_apps": ["com.example.learning"],
    }


def test_orm_rejects_policy_revision_update_and_delete(app: Flask) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Immutable policy")
        revision = _revision(policy)
        db.session.add_all([policy, revision])
        db.session.commit()

        revision.created_by = str(uuid4())
        with pytest.raises(PolicyRevisionImmutableError):
            db.session.commit()
        db.session.rollback()

        loaded_revision = db.session.get(PolicyRevision, revision.id)
        assert loaded_revision is not None
        loaded_revision.payload = {
            "schema_version": 1,
            "blocked_apps": ["com.example.changed"],
        }
        with pytest.raises(PolicyRevisionImmutableError):
            db.session.commit()
        db.session.rollback()

        stored_revision = db.session.get(PolicyRevision, loaded_revision.id)
        assert stored_revision is not None
        db.session.delete(stored_revision)
        with pytest.raises(PolicyRevisionImmutableError):
            db.session.commit()
        db.session.rollback()


def test_database_rejects_duplicate_revision_version_and_content(app: Flask) -> None:
    with app.app_context():
        policy = Policy(policy_uuid=uuid4(), name="Unique revisions")
        db.session.add_all([policy, _revision(policy)])
        db.session.commit()

        duplicate = _revision(policy, version=2)
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


@pytest.mark.parametrize("status", sorted(POLICY_STATUSES))
def test_policy_accepts_approved_statuses(status: str) -> None:
    assert Policy(policy_uuid=uuid4(), name="Lifecycle", status=status).status == status


@pytest.mark.parametrize("status", ["published", "", None, 1])
def test_policy_rejects_invalid_status_in_model(status: object) -> None:
    with pytest.raises(ValueError, match="invalid policy status"):
        Policy(policy_uuid=uuid4(), name="Invalid lifecycle", status=status)


def test_database_rejects_invalid_policy_status(app: Flask) -> None:
    with app.app_context():
        with pytest.raises(IntegrityError):
            db.session.execute(
                insert(Policy).values(
                    policy_uuid=uuid4(),
                    name="Invalid database policy",
                    status="published",
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
