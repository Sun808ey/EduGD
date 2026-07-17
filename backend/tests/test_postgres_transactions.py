from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.models import Device
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)
from test_support.postgres_transactions import isolated_postgres_session

pytestmark = pytest.mark.postgres


def test_fixture_commit_remains_in_outer_transaction(
    postgres_session,
    postgres_engine: Engine,
) -> None:
    probe_uuid = uuid4()
    postgres_session.add(Device(device_uuid=probe_uuid, android_version="test-only"))
    postgres_session.commit()

    assert (
        postgres_session.scalar(select(Device).where(Device.device_uuid == probe_uuid))
        is not None
    )
    with postgres_engine.connect() as independent_connection:
        visible_outside = independent_connection.scalar(
            select(Device.id).where(Device.device_uuid == probe_uuid)
        )

    assert visible_outside is None


def test_isolated_session_rolls_back_and_closes_completely(
    postgres_engine: Engine,
) -> None:
    approved = validate_postgres_test_environment(require_destructive=True)
    probe_uuid = uuid4()

    with isolated_postgres_session(postgres_engine, approved) as session:
        session.add(Device(device_uuid=probe_uuid, android_version="test-only"))
        session.commit()
        assert (
            session.scalar(select(Device).where(Device.device_uuid == probe_uuid))
            is not None
        )

    with postgres_engine.connect() as verification_connection:
        validate_connected_postgres_test_environment(
            verification_connection,
            approved,
            require_destructive=True,
        )
        persisted = verification_connection.scalar(
            select(Device.id).where(Device.device_uuid == probe_uuid)
        )

    assert persisted is None
