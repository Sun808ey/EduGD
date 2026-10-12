from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import g

import app.routes.auth as auth
from app.services.administrator_authentication import (
    AdministratorConflictError,
    AdministratorDatabaseError,
    AdministratorNotFoundError,
    AdministratorOperationError,
)
from app.services.administrator_login import AdministratorLoginDatabaseError


def _handler(function):
    return function.__wrapped__.__wrapped__


def _context(monkeypatch):
    context = SimpleNamespace(
        administrator=SimpleNamespace(
            id=1,
            username="admin",
            display_name="Admin",
            administrator_uuid=uuid4(),
        ),
        session=SimpleNamespace(id=2),
    )
    monkeypatch.setattr(auth, "get_administrator_request_context", lambda: context)
    return context


def _call(app, monkeypatch, function, *, payload=None, args=()):
    context = _context(monkeypatch)
    with app.test_request_context(json=payload):
        g.administrator_request_context = context
        return _handler(function)(*args)


def test_auth_logout_identity_and_login_error_routes(app, monkeypatch) -> None:
    context = _context(monkeypatch)
    with app.test_request_context("/api/v1/admin/auth/logout"):
        g.administrator_request_context = context
        monkeypatch.setattr(auth, "logout_administrator", lambda _context: None)
        assert _handler(auth.administrator_logout)().status_code == 200

    with app.test_request_context("/api/v1/admin/auth/logout"):
        g.administrator_request_context = context
        monkeypatch.setattr(
            auth,
            "logout_administrator",
            lambda _context: (_ for _ in ()).throw(auth.SQLAlchemyError("offline")),
        )
        assert _handler(auth.administrator_logout)().status_code == 500

    with app.test_request_context("/api/v1/admin/auth/me"):
        g.administrator_request_context = context
        monkeypatch.setattr(auth, "administrator_permissions", lambda _id: ["read"])
        assert _handler(auth.administrator_identity)().status_code == 200

    with app.test_request_context("/api/v1/admin/auth/me"):
        g.administrator_request_context = context
        monkeypatch.setattr(
            auth,
            "administrator_permissions",
            lambda _id: (_ for _ in ()).throw(auth.SQLAlchemyError("offline")),
        )
        assert _handler(auth.administrator_identity)().status_code == 500

    with app.test_request_context("/api/v1/admin/auth/login", json={}):
        monkeypatch.setattr(
            auth,
            "validate_administrator_login_request",
            lambda _request: (_ for _ in ()).throw(
                auth.AdministratorLoginValidationError(400)
            ),
        )
        assert auth.administrator_login().status_code == 400
    with app.test_request_context(
        "/api/v1/admin/auth/login", json={"username": "a", "password": "b"}
    ):
        monkeypatch.setattr(
            auth,
            "validate_administrator_login_request",
            lambda _request: SimpleNamespace(username="a", password="b"),
        )
        monkeypatch.setattr(
            auth,
            "authenticate_administrator",
            lambda **_: (_ for _ in ()).throw(
                AdministratorLoginDatabaseError("offline")
            ),
        )
        assert auth.administrator_login().status_code == 500


@pytest.mark.parametrize(
    "error, status",
    [
        (AdministratorConflictError("conflict"), 409),
        (AdministratorDatabaseError("database"), 500),
        (
            AdministratorOperationError(
                "authorized administrator credentials are required"
            ),
            403,
        ),
        (AdministratorOperationError("invalid"), 400),
    ],
)
def test_administrator_create_maps_errors(app, monkeypatch, error, status) -> None:
    payload = {
        "username": "new.admin",
        "display_name": "New Administrator",
        "password": "NewAdmin!2026",
        "operator_password": "Admin!2026",
        "reason": "approved account creation",
    }
    monkeypatch.setattr(
        auth,
        "create_administrator",
        lambda **_: (_ for _ in ()).throw(error),
    )
    response = _call(app, monkeypatch, auth.administrator_create, payload=payload)
    assert response.status_code == status


def test_administrator_create_and_list_detail_routes(app, monkeypatch) -> None:
    payload = {
        "username": "new.admin",
        "display_name": "New Administrator",
        "password": "NewAdmin!2026",
        "operator_password": "Admin!2026",
        "reason": "approved account creation",
    }
    monkeypatch.setattr(
        auth,
        "create_administrator",
        lambda **_: SimpleNamespace(
            administrator_uuid="admin-uuid", revoked_sessions=0
        ),
    )
    created = _call(app, monkeypatch, auth.administrator_create, payload=payload)
    assert created.status_code == 201

    monkeypatch.setattr(
        auth,
        "list_administrators",
        lambda **_: ([], 0),
    )
    with app.test_request_context("/admin/administrators?page=1&per_page=10"):
        g.administrator_request_context = _context(monkeypatch)
        assert _handler(auth.administrator_list)().status_code == 200
    with app.test_request_context("/admin/administrators?page=nope"):
        g.administrator_request_context = _context(monkeypatch)
        assert _handler(auth.administrator_list)().status_code == 400
    monkeypatch.setattr(
        auth,
        "list_administrators",
        lambda **_: (_ for _ in ()).throw(AdministratorDatabaseError("offline")),
    )
    with app.test_request_context():
        g.administrator_request_context = _context(monkeypatch)
        assert _handler(auth.administrator_list)().status_code == 500

    monkeypatch.setattr(auth, "_administrator_payload", lambda value: {"id": value})
    monkeypatch.setattr(auth, "get_administrator_by_uuid", lambda _value: "target")
    with app.test_request_context():
        g.administrator_request_context = _context(monkeypatch)
        assert _handler(auth.administrator_detail)(str(uuid4())).status_code == 200
    for error, status in [
        (AdministratorNotFoundError("missing"), 404),
        (AdministratorConflictError("conflict"), 409),
        (AdministratorDatabaseError("offline"), 500),
    ]:
        monkeypatch.setattr(
            auth,
            "get_administrator_by_uuid",
            lambda _value, error=error: (_ for _ in ()).throw(error),
        )
        with app.test_request_context():
            g.administrator_request_context = _context(monkeypatch)
            assert (
                _handler(auth.administrator_detail)(str(uuid4())).status_code == status
            )


def test_sensitive_administrator_mutations_cover_success_and_validation(
    app, monkeypatch
) -> None:
    target_uuid = str(uuid4())
    context = _context(monkeypatch)
    monkeypatch.setattr(
        auth, "authorize_administrator_operator", lambda **_: context.administrator
    )
    monkeypatch.setattr(
        auth,
        "get_administrator_by_uuid",
        lambda _value: SimpleNamespace(username="target"),
    )
    monkeypatch.setattr(
        auth,
        "replace_administrator_permissions",
        lambda **_: SimpleNamespace(administrator_uuid=target_uuid),
    )
    monkeypatch.setattr(
        auth,
        "revoke_administrator_sessions",
        lambda **_: SimpleNamespace(administrator_uuid=target_uuid, revoked_sessions=2),
    )
    monkeypatch.setattr(
        auth,
        "disable_administrator",
        lambda **_: SimpleNamespace(administrator_uuid=target_uuid, revoked_sessions=1),
    )
    monkeypatch.setattr(
        auth,
        "reset_administrator_password",
        lambda **_: SimpleNamespace(administrator_uuid=target_uuid, revoked_sessions=3),
    )
    with app.test_request_context(
        json={"permissions": ["policy.manage"], "operator_password": "x", "reason": "r"}
    ):
        g.administrator_request_context = context
        assert (
            _handler(auth.administrator_permissions_replace)(target_uuid).status_code
            == 200
        )
    with app.test_request_context(json={"operator_password": "x", "reason": "r"}):
        g.administrator_request_context = context
        assert (
            _handler(auth.administrator_sessions_revoke)(target_uuid).status_code == 200
        )
    with app.test_request_context(json={"operator_password": "x", "reason": "r"}):
        g.administrator_request_context = context
        monkeypatch.setattr(
            auth, "assert_administrator_may_be_disabled", lambda _value: None
        )
        assert _handler(auth.administrator_disable)(target_uuid).status_code == 200
    with app.test_request_context(
        json={"password": "NewPassword!2026", "operator_password": "x", "reason": "r"}
    ):
        g.administrator_request_context = context
        assert (
            _handler(auth.administrator_password_reset)(target_uuid).status_code == 200
        )
    with app.test_request_context(json={}):
        g.administrator_request_context = context
        assert (
            _handler(auth.administrator_permissions_replace)(target_uuid).status_code
            == 400
        )


@pytest.mark.parametrize(
    "function, payload",
    [
        (
            auth.administrator_permissions_replace,
            {"permissions": [], "operator_password": "x", "reason": "r"},
        ),
        (
            auth.administrator_sessions_revoke,
            {"operator_password": "x", "reason": "r"},
        ),
        (auth.administrator_disable, {"operator_password": "x", "reason": "r"}),
        (
            auth.administrator_password_reset,
            {
                "password": "NewPassword!2026",
                "operator_password": "x",
                "reason": "r",
            },
        ),
    ],
)
def test_sensitive_administrator_mutations_map_operation_errors(
    app, monkeypatch, function, payload
) -> None:
    context = _context(monkeypatch)
    monkeypatch.setattr(
        auth,
        "authorize_administrator_operator",
        lambda **_: (_ for _ in ()).throw(
            AdministratorOperationError(
                "authorized administrator credentials are required"
            )
        ),
    )
    with app.test_request_context(json=payload):
        g.administrator_request_context = context
        assert _handler(function)(str(uuid4())).status_code == 403


def test_auth_route_helpers_and_invalid_payload_paths(app, monkeypatch) -> None:
    with pytest.raises(TypeError):
        auth._administrator_payload(object())
    with pytest.raises(ValueError):
        auth._text({}, "required")
    assert (
        auth._administrator_operation_error(
            AdministratorOperationError("bad")
        ).status_code
        == 400
    )
    context = _context(monkeypatch)
    invalid_calls = [
        (auth.administrator_create, (), {}),
        (auth.administrator_sessions_revoke, (str(uuid4()),), {}),
        (auth.administrator_disable, (str(uuid4()),), {}),
        (auth.administrator_password_reset, (str(uuid4()),), {}),
    ]
    for function, args, payload in invalid_calls:
        with app.test_request_context(json=payload):
            g.administrator_request_context = context
            assert _handler(function)(*args).status_code == 400
    value_error_calls = [
        (
            auth.administrator_permissions_replace,
            (str(uuid4()),),
            {"permissions": [], "operator_password": 1, "reason": "r"},
        ),
        (
            auth.administrator_sessions_revoke,
            (str(uuid4()),),
            {"operator_password": 1, "reason": "r"},
        ),
        (
            auth.administrator_disable,
            (str(uuid4()),),
            {"operator_password": 1, "reason": "r"},
        ),
        (
            auth.administrator_password_reset,
            (str(uuid4()),),
            {"password": "NewPassword!2026", "operator_password": 1, "reason": "r"},
        ),
    ]
    for function, args, payload in value_error_calls:
        with app.test_request_context(json=payload):
            g.administrator_request_context = context
            assert _handler(function)(*args).status_code == 400
