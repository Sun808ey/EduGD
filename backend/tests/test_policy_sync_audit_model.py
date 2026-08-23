from uuid import uuid4

import pytest
from flask import Flask
from flask_migrate import downgrade
from sqlalchemy import CheckConstraint, DateTime, text

from app.extensions import db
from app.models import Device, PolicySynchronizationEvent


def test_policy_sync_audit_model_contract() -> None:
    table = PolicySynchronizationEvent.__table__
    assert table.name == "policy_synchronization_events"
    assert table.c.id.primary_key is True
    assert table.c.event_uuid.nullable is False
    assert table.c.device_id.nullable is True
    assert table.c.credential_id.nullable is True
    assert table.c.requested_device_pseudonym.nullable is False
    assert table.c.event_hash.nullable is False
    assert table.c.previous_event_hash.nullable is True
    assert isinstance(table.c.requested_at.type, DateTime)
    assert table.c.requested_at.type.timezone is True

    foreign_keys = {
        foreign_key.target_fullname: foreign_key.ondelete
        for foreign_key in table.foreign_keys
    }
    assert foreign_keys == {
        "device_credentials.id": "RESTRICT",
        "devices.id": "RESTRICT",
    }
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_policy_synchronization_events_client_version",
        "ck_policy_synchronization_events_device_pseudonym_length",
        "ck_policy_synchronization_events_hash_length",
        "ck_policy_synchronization_events_operation",
        "ck_policy_synchronization_events_outcome",
        "ck_policy_synchronization_events_previous_hash_length",
        "ck_policy_synchronization_events_server_version",
    }


def test_sync_audit_downgrade_refuses_to_discard_events(app: Flask) -> None:
    with app.app_context():
        device = Device(device_uuid=uuid4(), android_version="10", api_level=29)
        db.session.add(device)
        db.session.flush()
        db.session.add(
            PolicySynchronizationEvent(
                device_id=device.id,
                requested_device_pseudonym=b"p" * 32,
                operation="no_change",
                outcome_category="no_assignment",
                server_policy_version=0,
                event_hash=b"h" * 32,
            )
        )
        db.session.commit()
        with pytest.raises(SystemExit):
            downgrade(revision="c3f8a1d6e4b9")
        assert (
            db.session.scalar(text("SELECT version_num FROM alembic_version"))
            == "d9b4e7a2c6f1"
        )
