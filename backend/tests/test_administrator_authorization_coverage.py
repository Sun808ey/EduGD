from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

import app.administrator_authorization as authorization
import app.services.administrator_authentication as administrator_service
from app.extensions import db, jwt
from app.models import Administrator
from app.services.administrator_authentication import bootstrap_administrator


def test_authentication_failure_responses_and_time_normalization(app) -> None:
    with app.test_request_context("/api/v1/admin/auth/me"):
        assert authorization.authentication_failure_response().status_code == 401
        assert authorization.authorization_failure_response().status_code == 403
    with app.test_request_context("/public"):
        assert authorization.authentication_failure_response().status_code == 401
        assert authorization.authorization_failure_response().status_code == 403
    naive = datetime(2026, 9, 20, 12)
    aware = datetime(2026, 9, 20, 12, tzinfo=UTC)
    assert authorization._as_utc(naive).tzinfo == UTC
    assert authorization._as_utc(aware) == aware


def test_administrator_permissions_and_failure_audit_paths(app, monkeypatch) -> None:
    class Result:
        def scalars(self):
            return self

        def __iter__(self):
            return iter(["administrator.manage", "policy.manage"])

    events: list[object] = []

    class Session:
        def execute(self, _statement):
            return Result()

        def add(self, value):
            events.append(value)

        def commit(self):
            return None

        def rollback(self):
            return None

    monkeypatch.setattr(authorization, "db", SimpleNamespace(session=Session()))
    assert authorization.administrator_permissions(1) == [
        "administrator.manage",
        "policy.manage",
    ]
    with app.test_request_context(
        "/api/v1/admin/auth/me", environ_base={"REMOTE_ADDR": "127.0.0.1"}
    ):
        authorization._record_authorization_failure("denied", None, None)
        authorization._record_unverified_authentication_failure("invalid_token")
    assert len(events) == 2

    class FailingSession(Session):
        def commit(self):
            raise SQLAlchemyError("offline")

    monkeypatch.setattr(authorization, "db", SimpleNamespace(session=FailingSession()))
    with app.test_request_context("/api/v1/admin/auth/me"):
        authorization._record_authorization_failure("denied", None, None)
        authorization._record_unverified_authentication_failure("invalid_token")


@pytest.mark.parametrize(
    "claims, status",
    [
        ({}, "invalid_session"),
        ({"jti": "jti", "sub": "subject"}, "invalid_session"),
    ],
)
def test_administrator_context_rejects_invalid_claims(
    app, monkeypatch, claims, status
) -> None:
    monkeypatch.setattr(authorization, "get_jwt", lambda: claims)
    with (
        app.app_context(),
        pytest.raises(authorization.AdministratorSessionError) as error,
    ):
        authorization._load_current_administrator_context()
    assert error.value.failure_class == status


@pytest.mark.parametrize(
    "administrator, session, expected",
    [
        (
            SimpleNamespace(administrator_uuid="subject", status="active"),
            SimpleNamespace(
                revoked_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
            "revoked_session",
        ),
        (
            SimpleNamespace(administrator_uuid="subject", status="active"),
            SimpleNamespace(
                revoked_at=None, expires_at=datetime.now(UTC) - timedelta(hours=1)
            ),
            "expired_session",
        ),
        (
            SimpleNamespace(administrator_uuid="subject", status="disabled"),
            SimpleNamespace(
                revoked_at=None, expires_at=datetime.now(UTC) + timedelta(hours=1)
            ),
            "account_disabled",
        ),
        (
            SimpleNamespace(administrator_uuid="subject", status="locked"),
            SimpleNamespace(
                revoked_at=None, expires_at=datetime.now(UTC) + timedelta(hours=1)
            ),
            "account_locked",
        ),
        (
            SimpleNamespace(administrator_uuid="subject", status="pending"),
            SimpleNamespace(
                revoked_at=None, expires_at=datetime.now(UTC) + timedelta(hours=1)
            ),
            "invalid_session",
        ),
    ],
)
def test_administrator_context_maps_session_states(
    app, monkeypatch, administrator, session, expected
) -> None:
    class Result:
        def one_or_none(self):
            return session, administrator

    monkeypatch.setattr(
        authorization, "get_jwt", lambda: {"jti": "jti", "sub": "subject"}
    )
    monkeypatch.setattr(
        authorization,
        "db",
        SimpleNamespace(session=SimpleNamespace(execute=lambda _statement: Result())),
    )
    with (
        app.app_context(),
        pytest.raises(authorization.AdministratorSessionError) as error,
    ):
        authorization._load_current_administrator_context()
    assert error.value.failure_class == expected


def test_administrator_context_rejects_missing_row_and_supports_permission_lookup(
    app, monkeypatch
) -> None:
    class Result:
        def one_or_none(self):
            return None

        def scalar_one_or_none(self):
            return 1

    monkeypatch.setattr(
        authorization, "get_jwt", lambda: {"jti": "jti", "sub": "subject"}
    )
    session = SimpleNamespace(execute=lambda _statement: Result())
    monkeypatch.setattr(authorization, "db", SimpleNamespace(session=session))
    with app.app_context(), pytest.raises(authorization.AdministratorSessionError):
        authorization._load_current_administrator_context()
    assert authorization._has_permission(1, "policy.manage") is True


def test_logout_administrator_commits_and_rolls_back_on_failure(
    app, monkeypatch
) -> None:
    events: list[object] = []
    session = SimpleNamespace(
        id=3,
        revoked_at=None,
        revoked_by_administrator_id=None,
        revocation_reason=None,
    )
    context = SimpleNamespace(administrator=SimpleNamespace(id=1), session=session)
    fake_session = SimpleNamespace(
        add=lambda value: events.append(value),
        commit=lambda: None,
        rollback=lambda: None,
    )
    monkeypatch.setattr(authorization, "db", SimpleNamespace(session=fake_session))
    with app.app_context():
        authorization.logout_administrator(context)
    assert session.revocation_reason == "administrator logout"
    assert events

    def fail_commit():
        raise SQLAlchemyError("offline")

    fake_session.commit = fail_commit
    with app.app_context(), pytest.raises(SQLAlchemyError):
        authorization.logout_administrator(context)


def test_administrator_mutation_service_success_and_guard_paths(app) -> None:
    with app.app_context():
        bootstrap_administrator(
            username="mutation.admin",
            display_name="Mutation Administrator",
            password="MutationAdmin!2026",
            operator_subject="test:mutation",
            reason="mutation fixture",
        )
        administrator = db.session.execute(select(Administrator)).scalar_one()
        result = administrator_service.replace_administrator_permissions(
            administrator_uuid=str(administrator.administrator_uuid),
            permissions=["administrator.manage"],
            operator=administrator,
            operator_subject="test:mutation",
            reason="reduced permissions",
        )
        assert result.administrator_uuid == str(administrator.administrator_uuid)
        with pytest.raises(administrator_service.AdministratorConflictError):
            administrator_service.replace_administrator_permissions(
                administrator_uuid=str(administrator.administrator_uuid),
                permissions=[],
                operator=administrator,
                operator_subject="test:mutation",
                reason="unsafe lockout",
            )
        with pytest.raises(administrator_service.AdministratorOperationError):
            administrator_service.authorize_administrator_operator(
                operator_username="mutation.admin", operator_password=""
            )
        with pytest.raises(administrator_service.AdministratorOperationError):
            administrator_service.create_administrator(
                username="another.admin",
                display_name="Another Administrator",
                password="AnotherAdmin!2026",
                operator_username="mutation.admin",
                operator_password="",
                operator_subject="test:mutation",
                reason="invalid operator password",
            )


def test_jwt_error_callbacks_record_failures(app, monkeypatch) -> None:
    authorization.configure_administrator_jwt()
    failures: list[str] = []
    monkeypatch.setattr(
        authorization,
        "_record_unverified_authentication_failure",
        failures.append,
    )
    with app.test_request_context("/api/v1/admin/auth/me"):
        assert jwt._needs_fresh_token_callback({}, {}).status_code == 401
        assert jwt._revoked_token_callback({}, {}).status_code == 401
        assert jwt._token_verification_failed_callback({}, {}).status_code == 401
    assert failures == ["invalid_token", "revoked_session", "invalid_token"]


def test_administrator_required_fails_closed_on_database_error(
    app, monkeypatch
) -> None:
    decorated = authorization.administrator_required()(lambda: "ok")
    monkeypatch.setattr(
        authorization,
        "_load_current_administrator_context",
        lambda: (_ for _ in ()).throw(SQLAlchemyError("offline")),
    )
    with app.test_request_context("/api/v1/admin/auth/me"):
        assert decorated.__wrapped__().status_code == 401


def test_administrator_service_validation_and_database_failures(
    app, monkeypatch
) -> None:
    with app.app_context():
        for value in [None, "bad username", "A" * 65]:
            with pytest.raises(administrator_service.AdministratorOperationError):
                administrator_service._validate_username(value)
        for value in [None, "short", "administrator"]:
            with pytest.raises(administrator_service.AdministratorOperationError):
                administrator_service._validate_password(value, "admin")
        with pytest.raises(administrator_service.AdministratorOperationError):
            administrator_service.get_administrator_by_uuid("not-a-uuid")

        class FailingSession:
            def execute(self, _statement):
                raise SQLAlchemyError("offline")

            def scalar(self, _statement):
                raise SQLAlchemyError("offline")

            def scalars(self, _statement):
                raise SQLAlchemyError("offline")

            def rollback(self):
                return None

        monkeypatch.setattr(
            administrator_service, "db", SimpleNamespace(session=FailingSession())
        )
        with pytest.raises(administrator_service.AdministratorDatabaseError):
            administrator_service.list_administrators(offset=0, limit=10)
        with pytest.raises(administrator_service.AdministratorDatabaseError):
            administrator_service.get_administrator_by_uuid(str(uuid4()))
        with pytest.raises(administrator_service.AdministratorDatabaseError):
            administrator_service.create_administrator(
                username="database.admin",
                display_name="Database Administrator",
                password="DatabaseAdmin!2026",
                operator_username="operator.admin",
                operator_password="OperatorAdmin!2026",
                operator_subject="test:database",
                reason="database failure",
            )
        with pytest.raises(administrator_service.AdministratorDatabaseError):
            administrator_service.reset_administrator_password(
                username="operator.admin",
                password="ResetAdmin!2026",
                operator_subject="test:database",
                reason="database failure",
            )
        with pytest.raises(administrator_service.AdministratorDatabaseError):
            administrator_service.disable_administrator(
                username="operator.admin",
                operator_subject="test:database",
                reason="database failure",
            )
        with pytest.raises(administrator_service.AdministratorDatabaseError):
            administrator_service.revoke_administrator_sessions(
                username="operator.admin",
                operator_subject="test:database",
                reason="database failure",
            )
