from datetime import timedelta

from sqlalchemy import DateTime, Index, UniqueConstraint, Uuid
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable

from app.models import Device, utc_now


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
    assert table.c.status.nullable is False
    assert table.c.status.default.arg == "active"
    assert table.c.status.server_default.arg == "active"

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
