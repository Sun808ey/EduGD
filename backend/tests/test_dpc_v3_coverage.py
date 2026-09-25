import base64
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from test_policy_contract_v3 import policy

import app.routes.dpc_controls as routes
from app.extensions import db
from app.models import Administrator, Device
from app.policy_contract import PolicyContractError
from app.policy_contract_v3 import (
    build_policy_v3_envelope,
    sign_policy_v3_envelope,
    verify_policy_v3_envelope,
)
from app.services.administrator_authentication import bootstrap_administrator
from app.services.device_controls import DeviceControlConflict, report_usage


def test_v3_envelope_round_trip_and_tamper_detection() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    envelope = build_policy_v3_envelope(
        policy_uuid=str(uuid4()),
        revision_uuid=str(uuid4()),
        revision_number=1,
        issued_at="2026-09-22T12:00:00Z",
        signing_key_id="test-key",
        payload=policy(),
    )
    signed = sign_policy_v3_envelope(envelope, private)
    assert verify_policy_v3_envelope(signed, private.public_key()) == envelope
    signed["payload"]["screen_time"]["daily_limit_minutes"] = 121
    with pytest.raises(PolicyContractError):
        verify_policy_v3_envelope(signed, private.public_key())


@pytest.mark.parametrize(
    "field, value",
    [
        ("daily_limit_minutes", 0),
        ("reset_minute", 1440),
        ("web_filter", {"default_action": "invalid", "rules": []}),
    ],
)
def test_v3_rejects_invalid_limits_and_filter(field: str, value: object) -> None:
    payload = policy()
    if field == "web_filter":
        payload[field] = value
    else:
        payload["screen_time"][field] = value
    with pytest.raises(PolicyContractError):
        build_policy_v3_envelope(
            policy_uuid=str(uuid4()),
            revision_uuid=str(uuid4()),
            revision_number=1,
            issued_at="2026-09-22T12:00:00Z",
            signing_key_id="test-key",
            payload=payload,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "usage_date": "bad",
            "active_minutes": 1,
            "policy_uuid": str(uuid4()),
            "revision_uuid": str(uuid4()),
        },
        {
            "usage_date": "2026-09-22",
            "active_minutes": -1,
            "policy_uuid": str(uuid4()),
            "revision_uuid": str(uuid4()),
        },
    ],
)
def test_usage_reports_reject_invalid_payloads(app, payload: object) -> None:
    with app.app_context():
        device = Device(
            device_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            android_version="10",
            api_level=29,
        )
        db.session.add(device)
        db.session.commit()
        with pytest.raises(ValueError):
            report_usage(device, payload)


def test_v3_route_requires_device_authentication(client) -> None:
    response = client.get(
        "/api/v1/sync/v3/devices/550e8400-e29b-41d4-a716-446655440000/state"
    )
    assert response.status_code == 401


def test_device_control_service_persists_block_clear_and_usage(app) -> None:
    from app.services.device_controls import clear_block, set_block

    with app.app_context():
        bootstrap_administrator(
            username="control.admin",
            display_name="Control Admin",
            password="OfflineSchool!2026",
            operator_subject="test:control-admin",
            reason="control coverage fixture",
        )
        administrator_id = db.session.query(Administrator.id).scalar()
        device = Device(
            device_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            android_version="10",
            api_level=29,
        )
        db.session.add(device)
        db.session.commit()
        active = set_block(device.device_uuid, administrator_id, "teacher request")
        assert active.status == "active"
        with pytest.raises(DeviceControlConflict):
            set_block(device.device_uuid, administrator_id, "duplicate")
        cleared = clear_block(device.device_uuid, administrator_id, "lesson ended")
        assert cleared.status == "cleared"
        usage = report_usage(
            device,
            {
                "usage_date": "2026-09-22",
                "active_minutes": 10,
                "policy_uuid": str(uuid4()),
                "revision_uuid": str(uuid4()),
            },
        )
        assert usage.active_minutes == 10
        with pytest.raises(DeviceControlConflict):
            report_usage(
                device,
                {
                    "usage_date": "2026-09-22",
                    "active_minutes": 9,
                    "policy_uuid": str(uuid4()),
                    "revision_uuid": str(uuid4()),
                },
            )


def test_dpc_route_handlers_cover_success_and_failures(app, monkeypatch) -> None:
    import app.routes.dpc_controls as routes

    now = datetime.now(UTC)
    override = SimpleNamespace(
        version=1, status="active", reason="ok", issued_at=now, cleared_at=None
    )
    administrator = SimpleNamespace(id=1)
    context = SimpleNamespace(administrator=administrator)
    with app.test_request_context(json={"reason": "ok"}):
        from flask import g

        g.administrator_request_context = context
        monkeypatch.setattr(routes, "set_block", lambda *_args: override)
        response = routes.block.__wrapped__.__wrapped__(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code == 201
        monkeypatch.setattr(
            routes,
            "set_block",
            lambda *_args: (_ for _ in ()).throw(
                routes.DeviceControlConflict("already active")
            ),
        )
        response = routes.block.__wrapped__.__wrapped__(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code == 409
        monkeypatch.setattr(routes, "clear_block", lambda *_args: override)
        response = routes.unblock.__wrapped__.__wrapped__(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code == 200
        monkeypatch.setattr(
            routes,
            "clear_block",
            lambda *_args: (_ for _ in ()).throw(routes.DeviceControlError()),
        )
        response = routes.unblock.__wrapped__.__wrapped__(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code == 503
    with app.test_request_context(json={}):
        from flask import g

        g.device_authentication_context = SimpleNamespace(
            device=SimpleNamespace(device_uuid="550e8400-e29b-41d4-a716-446655440000")
        )
        monkeypatch.setattr(
            routes, "report_usage", lambda *_args: (_ for _ in ()).throw(ValueError())
        )
        response = routes.usage.__wrapped__("550e8400-e29b-41d4-a716-446655440000")
        assert response.status_code == 400


@pytest.mark.parametrize(
    "operation, error, status",
    [
        ("set_block", ValueError(), 400),
        ("set_block", routes.DeviceControlNotFound(), 404),
        ("set_block", routes.DeviceControlError(), 503),
        ("clear_block", ValueError(), 400),
        ("clear_block", routes.DeviceControlNotFound(), 404),
        ("clear_block", routes.DeviceControlConflict("no active block"), 409),
    ],
)
def test_dpc_admin_route_errors(app, monkeypatch, operation, error, status) -> None:
    from flask import g

    import app.routes.dpc_controls as routes

    with app.test_request_context(json={"reason": "ok"}):
        g.administrator_request_context = SimpleNamespace(
            administrator=SimpleNamespace(id=1)
        )
        monkeypatch.setattr(
            routes, operation, lambda *_args, error=error: (_ for _ in ()).throw(error)
        )
        handler = routes.block if operation == "set_block" else routes.unblock
        response = handler.__wrapped__.__wrapped__(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code == status


@pytest.mark.parametrize(
    "error, status",
    [
        (routes.DeviceControlConflict("conflict"), 409),
        (routes.DeviceControlError(), 503),
    ],
)
def test_dpc_usage_route_errors(app, monkeypatch, error, status) -> None:
    from flask import g

    import app.routes.dpc_controls as routes

    context = SimpleNamespace(
        device=SimpleNamespace(device_uuid="550e8400-e29b-41d4-a716-446655440000")
    )
    with app.test_request_context(json={}):
        g.device_authentication_context = context
        monkeypatch.setattr(
            routes, "get_device_authentication_context", lambda: context
        )
        monkeypatch.setattr(
            routes, "report_usage", lambda *_args: (_ for _ in ()).throw(error)
        )
        response = routes.usage.__wrapped__(context.device.device_uuid)
        assert response.status_code == status


def test_dpc_sync_route_reports_signing_configuration_errors(app, monkeypatch) -> None:
    import app.routes.dpc_controls as routes

    context = SimpleNamespace(
        device=SimpleNamespace(device_uuid="550e8400-e29b-41d4-a716-446655440000", id=1)
    )
    monkeypatch.setattr(routes, "get_device_authentication_context", lambda: context)
    with app.test_request_context():
        app.config["DPC_POLICY_SIGNING_PRIVATE_KEY"] = None
        assert routes.sync_v3.__wrapped__(context.device.device_uuid).status_code == 503
        app.config["DPC_POLICY_SIGNING_PRIVATE_KEY"] = "not-a-key"
        assert routes.sync_v3.__wrapped__(context.device.device_uuid).status_code == 503


def test_dpc_sync_route_returns_signed_empty_state(app, monkeypatch) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    context = SimpleNamespace(
        device=SimpleNamespace(device_uuid="550e8400-e29b-41d4-a716-446655440000", id=1)
    )
    private = Ed25519PrivateKey.generate()
    app.config["DPC_POLICY_SIGNING_PRIVATE_KEY"] = (
        base64.urlsafe_b64encode(private.private_bytes_raw()).rstrip(b"=").decode()
    )
    monkeypatch.setattr(routes, "get_device_authentication_context", lambda: context)

    original_session = routes.db.session

    class EmptySession:
        def scalar(self, _query):
            return None

        def remove(self):
            original_session.remove()

    monkeypatch.setattr(routes.db, "session", EmptySession())
    with app.test_request_context():
        response = routes.sync_v3.__wrapped__(context.device.device_uuid)
    assert response.status_code == 200
    assert response.get_json()["policy"] is None
    assert response.get_json()["override_state"]["protocol_version"] == 3


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": 3},
        {**policy(), "screen_time": {}},
        {
            **policy(),
            "web_filter": {"default_action": "allow", "rules": [{"bad": True}]},
        },
        {
            **policy(),
            "web_filter": {
                "default_action": "allow",
                "rules": [
                    {
                        "rule_id": "x",
                        "domain": "example.com",
                        "action": "block",
                        "reason": "ok",
                    },
                    {
                        "rule_id": "x",
                        "domain": "other.com",
                        "action": "block",
                        "reason": "ok",
                    },
                ],
            },
        },
    ],
)
def test_v3_rejects_malformed_policy_shapes(payload: object) -> None:
    from app.policy_contract_v3 import validate_policy_v3

    with pytest.raises(PolicyContractError):
        validate_policy_v3(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            **policy(),
            "web_filter": {
                "default_action": "allow",
                "rules": [
                    {
                        "rule_id": "x",
                        "domain": "example.com",
                        "action": "block",
                        "reason": "",
                    }
                ],
            },
        },
        {
            **policy(),
            "web_filter": {
                "default_action": "allow",
                "rules": [
                    {
                        "rule_id": "x",
                        "domain": "example.com",
                        "action": "invalid",
                        "reason": "ok",
                    }
                ],
            },
        },
        {
            **policy(),
            "web_filter": {
                "default_action": "allow",
                "rules": [
                    {
                        "rule_id": "x",
                        "domain": "example.com",
                        "action": "block",
                        "reason": "ok",
                    },
                    {
                        "rule_id": "y",
                        "domain": "example.com",
                        "action": "block",
                        "reason": "ok",
                    },
                ],
            },
        },
    ],
)
def test_v3_rejects_invalid_rule_details(payload: object) -> None:
    from app.policy_contract_v3 import validate_policy_v3

    with pytest.raises(PolicyContractError):
        validate_policy_v3(payload)


def test_v3_rejects_unencodable_domain() -> None:
    from app.policy_contract_v3 import normalize_domain

    with pytest.raises(PolicyContractError):
        normalize_domain("\ud800.example")
