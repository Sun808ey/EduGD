from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, Uuid, inspect
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    AdministratorSession,
)


def _constraint_names(model: Any, constraint_type: type[Any]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def _index_names(model: Any) -> set[str]:
    return {
        index.name
        for index in model.__table__.indexes
        if isinstance(index, Index) and index.name is not None
    }


def _administrator(**overrides: object) -> Administrator:
    values: dict[str, object] = {
        "username": "enrollment.admin",
        "display_name": "Enrollment Administrator",
        "password_verifier": "scrypt:test-verifier",
    }
    values.update(overrides)
    return Administrator(**values)


def test_administrator_metadata_contract() -> None:
    table = Administrator.__table__

    assert table.c.id.primary_key is True
    assert isinstance(table.c.administrator_uuid.type, Uuid)
    assert table.c.administrator_uuid.type.as_uuid is True
    assert table.c.username.type.length == 64
    assert table.c.display_name.type.length == 120
    assert table.c.password_verifier.type.length == 512
    assert table.c.lock_expires_at.nullable is True
    assert table.c.disabled_at.nullable is True
    assert _constraint_names(Administrator, UniqueConstraint) == {
        "uq_administrators_username",
        "uq_administrators_uuid",
    }
    assert _constraint_names(Administrator, CheckConstraint) == {
        "ck_administrators_display_name_bounded",
        "ck_administrators_failed_attempts",
        "ck_administrators_lifecycle",
        "ck_administrators_password_verifier",
        "ck_administrators_status",
        "ck_administrators_username_bounded",
    }
    assert _index_names(Administrator) == {"ix_administrators_status"}
    assert "password" not in table.c
    assert "raw_password" not in table.c


def test_administrator_permission_metadata_contract() -> None:
    table = AdministratorPermission.__table__

    assert table.c.administrator_id.nullable is False
    assert table.c.granted_by_administrator_id.nullable is True
    assert table.c.trusted_operator_subject.nullable is True
    assert {foreign_key.ondelete for foreign_key in table.foreign_keys} == {"RESTRICT"}
    assert _constraint_names(AdministratorPermission, UniqueConstraint) == {
        "uq_administrator_permissions_administrator_permission"
    }
    assert _constraint_names(AdministratorPermission, CheckConstraint) == {
        "ck_administrator_permissions_grant_actor",
        "ck_administrator_permissions_operator_bounded",
        "ck_administrator_permissions_permission",
        "ck_administrator_permissions_reason_bounded",
    }
    assert _index_names(AdministratorPermission) == {
        "ix_administrator_permissions_administrator"
    }


def test_administrator_session_metadata_contract() -> None:
    table = AdministratorSession.__table__

    assert table.c.jti_digest.type.length == 32
    assert table.c.source_address_pseudonym.type.length == 32
    assert table.c.expires_at.nullable is False
    assert {foreign_key.ondelete for foreign_key in table.foreign_keys} == {"RESTRICT"}
    assert _constraint_names(AdministratorSession, UniqueConstraint) == {
        "uq_administrator_sessions_jti_digest"
    }
    assert _constraint_names(AdministratorSession, CheckConstraint) == {
        "ck_administrator_sessions_expiry",
        "ck_administrator_sessions_jti_digest_length",
        "ck_administrator_sessions_revocation_metadata_bounded",
        "ck_administrator_sessions_revocation_state",
        "ck_administrator_sessions_source_pseudonym_length",
    }
    assert _index_names(AdministratorSession) == {
        "ix_administrator_sessions_administrator_expires"
    }
    assert "jti" not in table.c
    assert "access_token" not in table.c
    assert "jwt" not in table.c


def test_administrator_authentication_event_metadata_contract() -> None:
    table = AdministratorAuthenticationEvent.__table__

    assert isinstance(table.c.event_uuid.type, Uuid)
    assert table.c.event_uuid.type.as_uuid is True
    assert table.c.administrator_id.nullable is True
    assert table.c.session_id.nullable is True
    assert table.c.source_address_pseudonym.type.length == 32
    assert {foreign_key.ondelete for foreign_key in table.foreign_keys} == {"RESTRICT"}
    assert _constraint_names(
        AdministratorAuthenticationEvent,
        UniqueConstraint,
    ) == {"uq_administrator_authentication_events_uuid"}
    assert _constraint_names(
        AdministratorAuthenticationEvent,
        CheckConstraint,
    ) == {
        "ck_administrator_authentication_events_actor",
        "ck_administrator_authentication_events_category",
        "ck_administrator_authentication_events_failure_bounded",
        "ck_administrator_authentication_events_metadata_bounded",
        "ck_administrator_authentication_events_source_pseudonym_length",
    }
    assert _index_names(AdministratorAuthenticationEvent) == {
        "ix_administrator_authentication_events_administrator_created",
        "ix_administrator_authentication_events_category_created",
    }
    for sensitive_column in (
        "access_token",
        "jwt",
        "password",
        "raw_source_address",
        "submitted_username",
    ):
        assert sensitive_column not in table.c


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: _administrator(username="UPPERCASE"),
            "invalid administrator username",
        ),
        (
            lambda: _administrator(display_name="contains\nnewline"),
            "display name must contain",
        ),
        (
            lambda: _administrator(password_verifier="plaintext"),
            "invalid administrator password verifier",
        ),
        (
            lambda: _administrator(status="unknown"),
            "invalid administrator status",
        ),
        (
            lambda: _administrator(failed_attempts=6),
            "failed attempts must be between 0 and 5",
        ),
        (
            lambda: AdministratorPermission(
                administrator_id=1,
                permission="unknown",
                trusted_operator_subject="host-operator",
                reason="bootstrap",
            ),
            "invalid administrator permission",
        ),
        (
            lambda: AdministratorSession(
                administrator_id=1,
                jti_digest=b"short",
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            ),
            "JTI digest must contain 32 bytes",
        ),
        (
            lambda: AdministratorAuthenticationEvent(
                category="unknown",
            ),
            "invalid administrator authentication event category",
        ),
        (
            lambda: AdministratorAuthenticationEvent(
                category="login_failed",
                failure_class="Invalid Value",
            ),
            "invalid administrator authentication failure class",
        ),
        (
            lambda: AdministratorAuthenticationEvent(
                category="login_failed",
                source_address_pseudonym=b"short",
            ),
            "source address pseudonym must contain 32 bytes",
        ),
    ],
)
def test_administrator_models_reject_invalid_bounded_values(
    factory: Any,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


def test_administrator_models_persist_only_derived_security_material(
    app: Flask,
) -> None:
    now = datetime.now(UTC)

    with app.app_context():
        db.create_all()
        administrator = _administrator()
        db.session.add(administrator)
        db.session.flush()

        permission = AdministratorPermission(
            administrator_id=administrator.id,
            permission="enrollment_token.issue",
            trusted_operator_subject="host-operator",
            reason="initial school enrollment administration",
        )
        session = AdministratorSession(
            administrator_id=administrator.id,
            jti_digest=b"j" * 32,
            source_address_pseudonym=b"s" * 32,
            expires_at=now + timedelta(minutes=15),
        )
        event = AdministratorAuthenticationEvent(
            administrator_id=administrator.id,
            category="bootstrap",
            source_address_pseudonym=b"s" * 32,
            trusted_operator_subject="host-operator",
            reason="initial school administrator",
        )
        db.session.add_all((permission, session, event))
        db.session.commit()

        assert administrator.administrator_uuid is not None
        assert event.event_uuid is not None
        assert administrator.permissions == [permission]
        assert administrator.sessions == [session]
        assert administrator.authentication_events == [event]
        assert session.jti_digest == b"j" * 32
        assert event.source_address_pseudonym == b"s" * 32


def test_database_rejects_inconsistent_administrator_lifecycle(app: Flask) -> None:
    with app.app_context():
        db.create_all()
        with pytest.raises(IntegrityError):
            db.session.execute(
                Administrator.__table__.insert().values(
                    administrator_uuid=uuid4(),
                    username="locked.admin",
                    display_name="Locked Administrator",
                    password_verifier="scrypt:test-verifier",
                    status="locked",
                    failed_attempts=0,
                    lock_expires_at=datetime.now(UTC) + timedelta(minutes=15),
                )
            )
            db.session.commit()
        db.session.rollback()


def test_database_rejects_permission_without_grant_actor(app: Flask) -> None:
    with app.app_context():
        db.create_all()
        administrator = _administrator(username="permission.admin")
        db.session.add(administrator)
        db.session.commit()

        with pytest.raises(IntegrityError):
            db.session.execute(
                AdministratorPermission.__table__.insert().values(
                    administrator_id=administrator.id,
                    permission="administrator.manage",
                    reason="missing actor must fail closed",
                )
            )
            db.session.commit()
        db.session.rollback()


def test_database_rejects_incomplete_session_revocation(app: Flask) -> None:
    now = datetime.now(UTC)

    with app.app_context():
        db.create_all()
        administrator = _administrator(username="session.admin")
        db.session.add(administrator)
        db.session.commit()

        with pytest.raises(IntegrityError):
            db.session.execute(
                AdministratorSession.__table__.insert().values(
                    administrator_id=administrator.id,
                    jti_digest=b"r" * 32,
                    issued_at=now,
                    expires_at=now + timedelta(minutes=15),
                    revoked_at=now,
                    revocation_reason="missing revocation actor",
                )
            )
            db.session.commit()
        db.session.rollback()


def test_administrator_tables_downgrade_and_upgrade_on_sqlite(app: Flask) -> None:
    administrator_tables = {
        "administrators",
        "administrator_permissions",
        "administrator_sessions",
        "administrator_authentication_events",
    }

    with app.app_context():
        assert administrator_tables <= set(inspect(db.engine).get_table_names())

        downgrade(revision="c6f8a2d4e7b1")
        assert administrator_tables.isdisjoint(inspect(db.engine).get_table_names())
        assert "devices" in inspect(db.engine).get_table_names()

        upgrade(revision="head")
        assert administrator_tables <= set(inspect(db.engine).get_table_names())
