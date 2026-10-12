from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import g
from sqlalchemy.exc import SQLAlchemyError

import app.routes.devices as devices
from app.services.admin_read import AdminReadNotFoundError, AdminReadPersistenceError
from app.services.device_asset_privacy import (
    DeviceAssetConflict,
    DeviceAssetNotFound,
    DeviceAssetPrivacyError,
    DeviceAssetRetentionError,
)
from app.services.school_device_assets import (
    AssetRegistrationConflict,
    AssetRegistrationError,
)


def _handler(function):
    return function.__wrapped__.__wrapped__


def _context(monkeypatch):
    context = SimpleNamespace(administrator=SimpleNamespace(id=1))
    monkeypatch.setattr(devices, "get_administrator_request_context", lambda: context)
    return context


def _call(app, monkeypatch, function, *, payload=None, args=()):
    context = _context(monkeypatch)
    with app.test_request_context(json=payload):
        g.administrator_request_context = context
        return _handler(function)(*args)


def test_device_read_routes_map_errors(app, monkeypatch) -> None:
    for error, status in [
        (ValueError(), 400),
        (AdminReadNotFoundError(), 404),
        (AdminReadPersistenceError(), 503),
    ]:
        monkeypatch.setattr(
            devices,
            "get_device",
            lambda _value, error=error: (_ for _ in ()).throw(error),
        )
        assert (
            _call(
                app, monkeypatch, devices.admin_device_detail, args=(str(uuid4()),)
            ).status_code
            == status
        )
        monkeypatch.setattr(
            devices,
            "get_device_policy_assignment",
            lambda _value, error=error: (_ for _ in ()).throw(error),
        )
        assert (
            _call(
                app,
                monkeypatch,
                devices.admin_device_policy_assignment,
                args=(str(uuid4()),),
            ).status_code
            == status
        )


def test_device_asset_routes_map_mutation_errors(app, monkeypatch) -> None:
    fields = {
        "asset_number": "TAB-1",
        "manufacturer": "Maker",
        "model": "Model",
        "serial_number": "SERIAL-1",
        "android_version": "13",
        "api_level": 33,
        "date_received": "2026-09-20",
        "condition": "Good",
        "department": "ICT",
        "asset_lifecycle_status": "REGISTERED",
        "asset_notes": None,
    }
    assert (
        _call(
            app, monkeypatch, devices.create_school_device_asset, payload={}
        ).status_code
        == 400
    )
    for error, status in [
        (AssetRegistrationConflict(), 409),
        (AssetRegistrationError(), 400),
    ]:
        monkeypatch.setattr(
            devices,
            "register_asset",
            lambda _payload, error=error: (_ for _ in ()).throw(error),
        )
        assert (
            _call(
                app, monkeypatch, devices.create_school_device_asset, payload=fields
            ).status_code
            == status
        )

    for error, status in [
        (DeviceAssetNotFound(), 404),
        (DeviceAssetConflict(), 409),
        (DeviceAssetPrivacyError(), 400),
    ]:
        monkeypatch.setattr(
            devices,
            "correct_device_asset",
            lambda *_args, error=error, **_kwargs: (_ for _ in ()).throw(error),
        )
        assert (
            _call(
                app,
                monkeypatch,
                devices.correct_school_device_asset,
                payload=fields,
                args=(str(uuid4()),),
            ).status_code
            == status
        )

    assert (
        _call(
            app,
            monkeypatch,
            devices.correct_school_device_asset,
            payload={},
            args=(str(uuid4()),),
        ).status_code
        == 400
    )

    for error, status in [
        (DeviceAssetNotFound(), 404),
        (DeviceAssetRetentionError("not ready"), 409),
        (DeviceAssetPrivacyError(), 400),
    ]:
        monkeypatch.setattr(
            devices,
            "redact_retired_device",
            lambda *_args, error=error, **_kwargs: (_ for _ in ()).throw(error),
        )
        assert (
            _call(
                app,
                monkeypatch,
                devices.purge_retired_device_data,
                payload={"reason": "approved"},
                args=(str(uuid4()),),
            ).status_code
            == status
        )


def test_device_assignment_routes_cover_invalid_and_conflict_paths(
    app, monkeypatch
) -> None:
    assert devices._text("  valid ", 20) == "valid"
    with pytest.raises(ValueError):
        devices._text("\n", 20)
    row = SimpleNamespace(
        assignment_uuid=uuid4(),
        target_type="class",
        target_name="Senior One",
        responsible_officer="ICT",
        assigned_at=date(2026, 9, 20),
        expected_return_date=None,
        returned_at=None,
        issue_condition="Good",
        return_condition=None,
    )
    assert devices._assignment(row)["target_name"] == "Senior One"

    assert (
        _call(
            app, monkeypatch, devices.device_location_assignments, args=("bad",)
        ).status_code
        == 400
    )
    monkeypatch.setattr(
        devices,
        "db",
        SimpleNamespace(
            session=SimpleNamespace(
                scalars=lambda _query: (_ for _ in ()).throw(
                    SQLAlchemyError("offline")
                ),
                rollback=lambda: None,
            )
        ),
    )
    assert (
        _call(
            app, monkeypatch, devices.device_location_assignments, args=(str(uuid4()),)
        ).status_code
        == 400
    )

    assert (
        _call(
            app,
            monkeypatch,
            devices.create_device_location_assignment,
            payload={},
            args=(str(uuid4()),),
        ).status_code
        == 400
    )
    monkeypatch.setattr(
        devices,
        "db",
        SimpleNamespace(
            session=SimpleNamespace(scalar=lambda _query: None, rollback=lambda: None)
        ),
    )
    valid = {
        "target_type": "class",
        "target_name": "Senior One",
        "responsible_officer": "ICT",
        "assigned_at": "2026-09-20",
        "expected_return_date": None,
        "issue_condition": "Good",
    }
    assert (
        _call(
            app,
            monkeypatch,
            devices.create_device_location_assignment,
            payload=valid,
            args=(str(uuid4()),),
        ).status_code
        == 404
    )

    for error, status in [
        (DeviceAssetNotFound(), 404),
        (DeviceAssetPrivacyError(), 400),
    ]:
        monkeypatch.setattr(
            devices,
            "correct_location_assignment",
            lambda *_args, error=error, **_kwargs: (_ for _ in ()).throw(error),
        )
        assert (
            _call(
                app,
                monkeypatch,
                devices.correct_device_location_assignment,
                payload={"reason": "x"},
                args=(str(uuid4()), str(uuid4())),
            ).status_code
            == status
        )
    assert (
        _call(
            app,
            monkeypatch,
            devices.correct_device_location_assignment,
            payload={},
            args=(str(uuid4()), str(uuid4())),
        ).status_code
        == 400
    )
