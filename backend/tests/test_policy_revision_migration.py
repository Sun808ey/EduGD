import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.services.policy_sync import get_policy_sync_payload

LEGACY_REVISION = "f4a7c9e2b6d1"
HEAD_REVISION = "e4a1b7c9d2f6"


def _migration_app(database_path: Path) -> Flask:
    return create_app(
        "testing",
        {"SQLALCHEMY_DATABASE_URI": f"sqlite+pysqlite:///{database_path}"},
    )


def _seed_legacy_policy(app: Flask) -> tuple[str, str]:
    device_uuid = uuid4()
    policy_uuid = uuid4()
    blocked_apps = ["com.example.first", "com.example.second"]
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        try:
            connection.execute(
                text(
                    "INSERT INTO devices "
                    "(device_uuid, android_version, api_level) "
                    "VALUES (:device_uuid, '10', 29)"
                ),
                {"device_uuid": device_uuid.hex},
            )
            device_id = connection.scalar(
                text("SELECT id FROM devices WHERE device_uuid = :device_uuid"),
                {"device_uuid": device_uuid.hex},
            )
            connection.execute(
                text(
                    "INSERT INTO policies "
                    "(policy_uuid, name, version, status, blocked_apps) "
                    "VALUES (:policy_uuid, 'Legacy policy', 5, 'active', "
                    ":blocked_apps)"
                ),
                {
                    "policy_uuid": policy_uuid.hex,
                    "blocked_apps": json.dumps(blocked_apps),
                },
            )
            policy_id = connection.scalar(
                text("SELECT id FROM policies WHERE policy_uuid = :policy_uuid"),
                {"policy_uuid": policy_uuid.hex},
            )
            connection.execute(
                text(
                    "INSERT INTO device_policy_assignments "
                    "(device_id, policy_id, policy_version, status) "
                    "VALUES (:device_id, :policy_id, 5, 'active')"
                ),
                {"device_id": device_id, "policy_id": policy_id},
            )
            transaction.commit()
        finally:
            connection.close()
    return str(device_uuid), str(policy_uuid)


def test_sqlite_migration_converts_and_safely_downgrades_legacy_data(
    tmp_path: Path,
) -> None:
    app = _migration_app(tmp_path / "conversion.db")
    with app.app_context():
        upgrade(revision=LEGACY_REVISION)
    device_uuid, policy_uuid = _seed_legacy_policy(app)

    with app.app_context():
        upgrade(revision="head")
        inspector = inspect(db.engine)
        assert "policy_revisions" in inspector.get_table_names()
        assert {column["name"] for column in inspector.get_columns("policies")} == {
            "id",
            "policy_uuid",
            "name",
            "status",
            "created_at",
            "updated_at",
        }
        assignment_columns = {
            column["name"]
            for column in inspector.get_columns("device_policy_assignments")
        }
        assert "policy_revision_id" in assignment_columns
        assert "policy_id" not in assignment_columns
        assert "policy_version" not in assignment_columns

        revision = db.session.execute(
            text(
                "SELECT version, payload, content_hash, created_by "
                "FROM policy_revisions"
            )
        ).one()
        payload = json.loads(revision.payload)
        canonical = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        assert revision.version == 5
        assert payload == {
            "schema_version": 1,
            "blocked_apps": ["com.example.first", "com.example.second"],
        }
        assert bytes(revision.content_hash) == hashlib.sha256(canonical).digest()
        assert revision.created_by.startswith("migration:")
        assert get_policy_sync_payload(device_uuid)["policy"] == {
            "policy_uuid": policy_uuid,
            "policy_version": 5,
            "blocked_apps": ["com.example.first", "com.example.second"],
        }

        db.session.remove()
        downgrade(revision=LEGACY_REVISION)
        restored = db.session.execute(
            text(
                "SELECT policy.version, policy.blocked_apps, "
                "assignment.policy_version "
                "FROM policies AS policy "
                "JOIN device_policy_assignments AS assignment "
                "ON assignment.policy_id = policy.id"
            )
        ).one()
        assert restored.version == 5
        assert json.loads(restored.blocked_apps) == [
            "com.example.first",
            "com.example.second",
        ]
        assert restored.policy_version == 5

        upgrade(revision="head")
        assert (
            db.session.scalar(text("SELECT version_num FROM alembic_version"))
            == HEAD_REVISION
        )


def test_sqlite_downgrade_refuses_to_discard_revision_history(
    tmp_path: Path,
) -> None:
    app = _migration_app(tmp_path / "refusal.db")
    with app.app_context():
        upgrade(revision=LEGACY_REVISION)
    _seed_legacy_policy(app)

    with app.app_context():
        upgrade(revision="head")
        first = db.session.execute(text("SELECT policy_id FROM policy_revisions")).one()
        payload = {"schema_version": 1, "blocked_apps": ["com.example.new"]}
        canonical = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        db.session.execute(
            text(
                "INSERT INTO policy_revisions "
                "(revision_uuid, policy_id, version, payload, content_hash, "
                "created_by) VALUES (:uuid, :policy_id, 6, :payload, :hash, "
                ":actor)"
            ),
            {
                "uuid": uuid4().hex,
                "policy_id": first.policy_id,
                "payload": json.dumps(payload),
                "hash": hashlib.sha256(canonical).digest(),
                "actor": str(uuid4()),
            },
        )
        db.session.commit()
        db.session.remove()

        with pytest.raises(SystemExit):
            downgrade(revision=LEGACY_REVISION)

        assert (
            db.session.scalar(text("SELECT version_num FROM alembic_version"))
            == "d9b4e7a2c6f1"
        )
        assert db.session.scalar(text("SELECT count(*) FROM policy_revisions")) == 2


def test_actor_migration_refuses_unverified_revision_subject(
    tmp_path: Path,
) -> None:
    app = _migration_app(tmp_path / "actor-refusal.db")
    with app.app_context():
        upgrade(revision=LEGACY_REVISION)
    _seed_legacy_policy(app)

    with app.app_context():
        upgrade(revision="a8d5e2f7c1b4")
        db.session.execute(
            text(
                "UPDATE policy_revisions SET created_by = :actor "
                "WHERE created_by LIKE 'migration:%'"
            ),
            {"actor": str(uuid4())},
        )
        db.session.commit()
        db.session.remove()

        with pytest.raises(SystemExit):
            upgrade(revision="head")

        assert (
            db.session.scalar(text("SELECT version_num FROM alembic_version"))
            == "a8d5e2f7c1b4"
        )
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("policy_revisions")
        }
        assert "created_by_administrator_id" not in columns
