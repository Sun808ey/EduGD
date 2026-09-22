from datetime import timedelta
from uuid import uuid4

import pytest
from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    UniqueConstraint,
    Uuid,
    insert,
    inspect,
    text,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from app.extensions import db
from app.models import DEVICE_STATUSES, Device, DevicePolicyAssignment, utc_now


def test_device_model_contract() -> None:
    table = Device.__table__

    assert table.name == "devices"
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False

    assert isinstance(table.c.device_uuid.type, Uuid)
    assert table.c.device_uuid.type.as_uuid is True
    assert table.c.device_uuid.nullable is False

    unique_constraints = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("device_uuid",) in unique_constraints

    indexes = {
        tuple(index.columns.keys())
        for index in table.indexes
        if isinstance(index, Index)
    }
    assert ("device_uuid",) in indexes

    assert table.c.android_version.nullable is False
    assert table.c.api_level.nullable is False
    assert table.c.status.nullable is False
    assert table.c.status.default.arg == "active"
    assert table.c.status.server_default.arg == "active"
    status_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_devices_status" in status_constraints
    assert "ck_devices_api_level_supported" in status_constraints
    assert "ck_devices_android_api_match" in status_constraints

    assert table.c.registered_at.nullable is False
    assert table.c.last_sync_at.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert table.c.updated_at.onupdate is not None

    timestamp_columns = (
        table.c.registered_at,
        table.c.last_sync_at,
        table.c.created_at,
        table.c.updated_at,
    )
    assert all(isinstance(column.type, DateTime) for column in timestamp_columns)
    assert all(column.type.timezone is True for column in timestamp_columns)

    postgresql_ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    sqlite_ddl = str(CreateTable(table).compile(dialect=sqlite.dialect()))
    assert "UUID" in postgresql_ddl
    assert "CHAR(32)" in sqlite_ddl


def test_device_timestamp_source_is_utc_aware() -> None:
    timestamp = utc_now()

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() == timedelta(0)


@pytest.mark.parametrize("status", sorted(DEVICE_STATUSES))
def test_device_accepts_approved_statuses(status: str) -> None:
    device = Device(
        device_uuid=uuid4(),
        android_version="10",
        api_level=29,
        status=status,
    )

    assert device.status == status


def test_device_rejects_invalid_status_in_model() -> None:
    with pytest.raises(ValueError, match="invalid device status"):
        Device(
            device_uuid=uuid4(),
            android_version="10",
            api_level=29,
            status="lost",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("android_version", "11", "unsupported Android version"),
        ("api_level", 30, "unsupported Android API level"),
        ("api_level", True, "unsupported Android API level"),
    ],
)
def test_device_rejects_unsupported_android_metadata(
    field: str,
    value: object,
    message: str,
) -> None:
    values: dict[str, object] = {
        "device_uuid": uuid4(),
        "android_version": "10",
        "api_level": 29,
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        Device(**values)


def test_database_rejects_android_api_mismatch(app: Flask) -> None:
    with app.app_context():
        with pytest.raises(IntegrityError):
            db.session.execute(
                insert(Device).values(
                    device_uuid=uuid4(),
                    android_version="10",
                    api_level=28,
                )
            )
            db.session.commit()
        db.session.rollback()


def test_database_rejects_invalid_device_status(app: Flask) -> None:
    with app.app_context():
        with pytest.raises(IntegrityError):
            db.session.execute(
                insert(Device).values(
                    device_uuid=uuid4(),
                    android_version="10",
                    api_level=29,
                    status="lost",
                )
            )
            db.session.commit()
        db.session.rollback()


def test_sqlite_enforces_foreign_keys(app: Flask) -> None:
    with app.app_context():
        assert db.session.scalar(text("PRAGMA foreign_keys")) == 1
        with pytest.raises(IntegrityError):
            db.session.execute(
                insert(DevicePolicyAssignment).values(
                    device_id=-1,
                    policy_revision_id=-1,
                    status="active",
                    trusted_operator_subject="test:foreign-key-fixture",
                    reason="foreign key enforcement fixture",
                )
            )
            db.session.commit()
        db.session.rollback()


def test_device_identity_migration_downgrades_and_upgrades_on_sqlite(
    app: Flask,
) -> None:
    with app.app_context():
        downgrade(revision="7c91b8e2d4a6")
        downgraded_checks = {
            constraint["name"]
            for constraint in inspect(db.engine).get_check_constraints("devices")
        }

        upgrade(revision="head")
        upgraded_checks = {
            constraint["name"]
            for constraint in inspect(db.engine).get_check_constraints("devices")
        }

    assert "ck_devices_api_level_supported" not in downgraded_checks
    assert "ck_devices_android_api_match" not in downgraded_checks
    assert "ck_devices_api_level_supported" in upgraded_checks
    assert "ck_devices_android_api_match" in upgraded_checks
