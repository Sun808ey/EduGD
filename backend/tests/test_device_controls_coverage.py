from uuid import UUID, uuid4

import pytest

from app.extensions import db
from app.models import Device
from app.services.administrator_authentication import bootstrap_administrator
from app.services.device_controls import (
    DeviceControlConflict,
    DeviceControlNotFound,
    _reason,
    clear_block,
    report_usage,
    set_block,
)


def _device(app) -> UUID:
    with app.app_context():
        bootstrap_administrator(
            username=f"controls-{uuid4().hex[:10]}",
            display_name="Controls Administrator",
            password="OfflineSchool!2026",
            operator_subject="test:controls",
            reason="coverage fixture",
        )
        device = Device(
            device_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            android_version="10",
            api_level=29,
        )
        db.session.add(device)
        db.session.commit()
        return device.device_uuid


@pytest.mark.parametrize("value", [None, "", "  ", "bad\nreason", "x" * 513])
def test_control_reason_validation_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        _reason(value)


def test_block_control_reactivates_and_rejects_missing_device(app) -> None:
    device_uuid = _device(app)
    with app.app_context():
        with pytest.raises(DeviceControlNotFound):
            set_block(uuid4(), 1, "missing")
        set_block(device_uuid, 1, "first")
        clear_block(device_uuid, 1, "clear")
        reactivated = set_block(device_uuid, 1, "second")
        assert reactivated.version == 2


def test_clear_control_rejects_missing_override(app) -> None:
    device_uuid = _device(app)
    with app.app_context(), pytest.raises(DeviceControlConflict):
        clear_block(device_uuid, 1, "nothing to clear")


def test_usage_control_accepts_idempotent_report(app) -> None:
    device_uuid = _device(app)
    payload = {
        "usage_date": "2026-09-24",
        "active_minutes": 12,
        "policy_uuid": str(uuid4()),
        "revision_uuid": str(uuid4()),
    }
    with app.app_context():
        device = db.session.query(Device).filter_by(device_uuid=device_uuid).one()
        first = report_usage(device, payload)
        second = report_usage(device, payload)
        assert second.id == first.id
        assert second.active_minutes == 12
