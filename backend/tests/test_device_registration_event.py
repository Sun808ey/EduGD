from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, Uuid, inspect

from app.extensions import db
from app.models import DeviceRegistrationEvent


def test_device_registration_event_model_contract() -> None:
    table = DeviceRegistrationEvent.__table__

    assert table.name == "device_registration_events"
    assert table.c.id.primary_key is True
    assert isinstance(table.c.event_uuid.type, Uuid)
    assert table.c.event_uuid.type.as_uuid is True
    assert table.c.device_id.nullable is False
    assert table.c.event_type.nullable is False
    assert table.c.stored_android_version.nullable is False
    assert table.c.stored_api_level.nullable is False
    assert table.c.reported_android_version.nullable is False
    assert table.c.reported_api_level.nullable is False
    assert table.c.created_at.nullable is False

    unique_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_device_registration_events_uuid" in unique_constraints

    check_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_constraints == {
        "ck_device_registration_events_reported_api_level",
        "ck_device_registration_events_stored_api_level",
        "ck_device_registration_events_type",
    }

    indexes = {index.name for index in table.indexes if isinstance(index, Index)}
    assert indexes == {"ix_device_registration_events_device_created"}


def test_registration_event_migration_downgrades_and_upgrades_on_sqlite(
    app: Flask,
) -> None:
    with app.app_context():
        downgrade(revision="9d2f4a6c8e10")
        assert "device_registration_events" not in inspect(db.engine).get_table_names()

        upgrade(revision="head")
        assert "device_registration_events" in inspect(db.engine).get_table_names()
