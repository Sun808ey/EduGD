from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Administrator, Policy
from app.services.policy_administration import (
    PolicyAdministrationConflict,
    PolicyAdministrationError,
    PolicyAdministrationNotFound,
    add_revision,
    create_policy,
    set_lifecycle,
)

PAYLOAD = {"schema_version": 1, "blocked_apps": ["org.example.reader"]}


def _administrator(status: str = "active") -> Administrator:
    lifecycle: dict[str, object] = {}
    if status == "locked":
        lifecycle = {
            "failed_attempts": 5,
            "lock_expires_at": datetime.now(UTC) + timedelta(minutes=10),
        }
    elif status == "disabled":
        lifecycle = {"disabled_at": datetime.now(UTC)}
    administrator = Administrator(
        username=f"policy-admin-{uuid4().hex[:10]}",
        display_name="Policy Administrator",
        password_verifier="scrypt:test-verifier",
        status=status,
        **lifecycle,
    )
    db.session.add(administrator)
    db.session.flush()
    return administrator


def test_policy_administration_creates_and_revises_policy(app) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()
        policy = create_policy(
            name="Offline policy", payload=PAYLOAD, administrator_id=administrator.id
        )
        revision = add_revision(
            policy_uuid=policy.policy_uuid,
            payload={"schema_version": 1, "blocked_apps": []},
            administrator_id=administrator.id,
        )
        assert policy.status == "draft"
        assert revision.version == 2


@pytest.mark.parametrize("value", [None, "", "  ", "x\nname", "x" * 256])
def test_create_policy_rejects_invalid_name(app, value: object) -> None:
    with app.app_context():
        with pytest.raises(ValueError):
            create_policy(name=value, payload=PAYLOAD, administrator_id=1)


def test_policy_administration_rejects_unavailable_or_missing_administrator(
    app,
) -> None:
    with app.app_context():
        disabled = _administrator("locked")
        db.session.commit()
        with pytest.raises(PolicyAdministrationError):
            create_policy(
                name="Unavailable", payload=PAYLOAD, administrator_id=disabled.id
            )
        with pytest.raises(PolicyAdministrationError):
            create_policy(name="Missing", payload=PAYLOAD, administrator_id=99999)


def test_policy_administration_handles_missing_policy_and_lifecycle(app) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()
        with pytest.raises(PolicyAdministrationNotFound):
            add_revision(
                policy_uuid=uuid4(), payload=PAYLOAD, administrator_id=administrator.id
            )
        with pytest.raises(ValueError):
            set_lifecycle(policy_uuid=uuid4(), status="draft")
        with pytest.raises(PolicyAdministrationNotFound):
            set_lifecycle(policy_uuid=uuid4(), status="active")
        policy = Policy(policy_uuid=uuid4(), name="Lifecycle")
        db.session.add(policy)
        db.session.commit()
        assert set_lifecycle(
            policy_uuid=policy.policy_uuid, status="active"
        ).status == ("active")


def test_policy_administration_rolls_back_database_errors(app, monkeypatch) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()

        def fail_commit() -> None:
            raise SQLAlchemyError("forced test failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyAdministrationError):
            create_policy(
                name="Rollback", payload=PAYLOAD, administrator_id=administrator.id
            )


def test_policy_administration_maps_integrity_errors(app, monkeypatch) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()

        def fail_commit() -> None:
            raise IntegrityError("statement", {}, None)

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyAdministrationConflict):
            create_policy(
                name="Conflict", payload=PAYLOAD, administrator_id=administrator.id
            )


def test_policy_administration_maps_revision_and_lifecycle_database_errors(
    app, monkeypatch
) -> None:
    with app.app_context():
        administrator = _administrator()
        policy = Policy(policy_uuid=uuid4(), name="Persistence")
        db.session.add(policy)
        db.session.commit()
        with pytest.raises(PolicyAdministrationError):
            add_revision(
                policy_uuid=policy.policy_uuid,
                payload=PAYLOAD,
                administrator_id=99999,
            )

        def fail_commit() -> None:
            raise SQLAlchemyError("forced test failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyAdministrationError):
            add_revision(
                policy_uuid=policy.policy_uuid,
                payload=PAYLOAD,
                administrator_id=administrator.id,
            )
        with pytest.raises(PolicyAdministrationError):
            set_lifecycle(policy_uuid=policy.policy_uuid, status="active")
