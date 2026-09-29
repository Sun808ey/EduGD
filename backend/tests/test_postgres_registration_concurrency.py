from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from flask import Flask
from sqlalchemy import delete, func, select

from app.extensions import db
from app.models import Device, DeviceRegistrationEvent
from app.schemas import DeviceRegistrationData
from app.services import device_registration as registration_service
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

pytestmark = [pytest.mark.postgres, pytest.mark.concurrency]


def test_concurrent_duplicate_registration_is_race_safe_and_audited(
    postgres_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approved = validate_postgres_test_environment(require_destructive=True)
    device_uuid = uuid4()
    lookup_barrier = Barrier(2, timeout=15)
    original_find_device = registration_service._find_device

    def synchronized_initial_lookup(candidate_uuid: UUID) -> Device | None:
        existing_device = original_find_device(candidate_uuid)
        if existing_device is None:
            lookup_barrier.wait()
        return existing_device

    monkeypatch.setattr(
        registration_service,
        "_find_device",
        synchronized_initial_lookup,
    )

    def register_once() -> bool:
        with postgres_app.app_context():
            try:
                result = registration_service.register_device(
                    DeviceRegistrationData(
                        device_uuid=device_uuid,
                        android_version="10",
                        api_level=29,
                    )
                )
                return result.created
            finally:
                db.session.remove()

    with postgres_app.app_context():
        with db.engine.connect() as connection:
            validate_connected_postgres_test_environment(
                connection,
                approved,
                require_destructive=True,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            created_results = list(executor.map(lambda _: register_once(), range(2)))

        with postgres_app.app_context():
            device_count = db.session.scalar(
                select(func.count())
                .select_from(Device)
                .where(Device.device_uuid == device_uuid)
            )
            event_types = db.session.scalars(
                select(DeviceRegistrationEvent.event_type)
                .join(Device)
                .where(Device.device_uuid == device_uuid)
                .order_by(DeviceRegistrationEvent.id)
            ).all()
            db.session.remove()

        assert sorted(created_results) == [False, True]
        assert device_count == 1
        assert event_types == ["registered", "duplicate"]
    finally:
        with postgres_app.app_context():
            stored_device_id = db.session.scalar(
                select(Device.id).where(Device.device_uuid == device_uuid)
            )
            if stored_device_id is not None:
                db.session.execute(
                    delete(DeviceRegistrationEvent).where(
                        DeviceRegistrationEvent.device_id == stored_device_id
                    )
                )
                db.session.execute(delete(Device).where(Device.id == stored_device_id))
                db.session.commit()
            db.session.remove()

    with postgres_app.app_context():
        assert (
            db.session.scalar(
                select(func.count())
                .select_from(Device)
                .where(Device.device_uuid == device_uuid)
            )
            == 0
        )
        assert (
            db.session.scalar(
                select(func.count())
                .select_from(DeviceRegistrationEvent)
                .join(Device)
                .where(Device.device_uuid == device_uuid)
            )
            == 0
        )
        db.session.remove()
