from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from test_policy_contract_v3 import policy as v3_policy

from app.extensions import db
from app.models import (
    Administrator,
    Device,
    DevicePolicyAssignment,
    ManagedApplication,
    Policy,
)
from app.services.policy_administration import (
    PolicyAdministrationConflict,
    PolicyAdministrationError,
    PolicyAdministrationNotFound,
    add_revision,
    create_policy,
    set_lifecycle,
)

PAYLOAD = {"schema_version": 1, "blocked_apps": ["org.example.reader"]}


def _administrator(status: str = "active") -> Administrator:
    lifecycle: dict[str, object] = {}
    if status == "locked":
        lifecycle = {
            "failed_attempts": 5,
            "lock_expires_at": datetime.now(UTC) + timedelta(minutes=10),
        }
    elif status == "disabled":
        lifecycle = {"disabled_at": datetime.now(UTC)}
    administrator = Administrator(
        username=f"policy-admin-{uuid4().hex[:10]}",
        display_name="Policy Administrator",
        password_verifier="scrypt:test-verifier",
        status=status,
        **lifecycle,
    )
    db.session.add(administrator)
    db.session.flush()
    return administrator


def test_policy_administration_creates_and_revises_policy(app) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()
        policy = create_policy(
            name="Offline policy", payload=PAYLOAD, administrator_id=administrator.id
        )
        revision = add_revision(
            policy_uuid=policy.policy_uuid,
            payload={"schema_version": 1, "blocked_apps": []},
            administrator_id=administrator.id,
        )
        assert policy.status == "draft"
        assert revision.version == 2


def test_policy_code_must_be_unique_at_creation(app) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()
        first = v3_policy()
        first["policy_code"] = "UNIQUE_POLICY"
        first["description"] = "First policy description"
        create_policy(
            name="Unique policy one",
            payload=first,
            administrator_id=administrator.id,
        )

        second = v3_policy()
        second["policy_code"] = "UNIQUE_POLICY"
        second["description"] = "Second policy description"
        with pytest.raises(PolicyAdministrationConflict, match="policy code"):
            create_policy(
                name="Unique policy two",
                payload=second,
                administrator_id=administrator.id,
            )


def test_policy_administration_materializes_approved_application_catalogue(app) -> None:
    with app.app_context():
        administrator = _administrator()
        application_uuid = uuid4()
        application = ManagedApplication(
            application_uuid=application_uuid,
            display_name="Catalogue learning app",
            package_name="org.catalogue.learning",
            category="learning",
            education_approved=True,
            mandatory_block=False,
            status="enabled",
        )
        db.session.add(application)
        db.session.commit()

        payload = v3_policy()
        payload["approved_applications"] = [
            {
                "application_uuid": str(application_uuid),
                "display_name": "Untrusted browser value",
                "package_name": "org.attacker.spoof",
                "application_type": "learning_application",
                "required": True,
                "allow_in_kiosk": True,
            }
        ]
        created = create_policy(
            name="Catalogue policy",
            payload=payload,
            administrator_id=administrator.id,
        )

        materialized = created.revisions[0].payload["approved_applications"][0]
        assert materialized["display_name"] == "Catalogue learning app"
        assert materialized["package_name"] == "org.catalogue.learning"


def test_policy_administration_materializes_file_sharing_catalogue_packages(
    app,
) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.add(
            ManagedApplication(
                application_uuid=uuid4(),
                display_name="Catalogue file sharing app",
                package_name="org.catalogue.fileshare",
                category="file_sharing",
                education_approved=False,
                mandatory_block=True,
                status="enabled",
            )
        )
        db.session.commit()

        payload = v3_policy()
        payload["application_controls"] = {
            "allow_installation_of_other_applications": False,
            "allow_installation_from_unknown_sources": False,
            "allow_uninstall_of_approved_applications": False,
            "allow_disable_of_approved_applications": False,
            "allow_google_play_store": False,
            "allow_file_sharing_applications": False,
        }
        created = create_policy(
            name="Application controls policy",
            payload=payload,
            administrator_id=administrator.id,
        )

        controls = created.revisions[0].payload["application_controls"]
        assert controls["file_sharing_packages"] == ["org.catalogue.fileshare"]


def test_required_approved_application_cannot_be_removed_from_active_assignment(
    app,
) -> None:
    with app.app_context():
        administrator = _administrator()
        application = ManagedApplication(
            application_uuid=uuid4(),
            display_name="Required learning app",
            package_name="org.catalogue.required",
            category="learning",
            education_approved=True,
            mandatory_block=False,
            status="enabled",
        )
        db.session.add(application)
        db.session.commit()

        payload = v3_policy()
        payload["approved_applications"] = [
            {
                "application_uuid": str(application.application_uuid),
                "application_type": "learning_application",
                "required": True,
                "allow_in_kiosk": True,
            }
        ]
        created = create_policy(
            name="Assigned catalogue policy",
            payload=payload,
            administrator_id=administrator.id,
        )
        device = Device(
            device_uuid=uuid4(),
            android_version="10",
            api_level=29,
            status="active",
        )
        db.session.add(device)
        db.session.flush()
        db.session.add(
            DevicePolicyAssignment(
                device_id=device.id,
                policy_revision_id=created.revisions[0].id,
                trusted_operator_subject="test:assignment",
                reason="required application fixture",
                status="active",
            )
        )
        db.session.commit()

        replacement = v3_policy()
        replacement["approved_applications"] = [
            {
                "application_uuid": str(application.application_uuid),
                "application_type": "learning_application",
                "required": False,
                "allow_in_kiosk": True,
            }
        ]
        with pytest.raises(
            PolicyAdministrationConflict,
            match="required application cannot be removed",
        ):
            add_revision(
                policy_uuid=created.policy_uuid,
                payload=replacement,
                administrator_id=administrator.id,
            )

        with pytest.raises(
            PolicyAdministrationConflict,
            match="required application cannot be removed",
        ):
            add_revision(
                policy_uuid=created.policy_uuid,
                payload=v3_policy(),
                administrator_id=administrator.id,
            )


@pytest.mark.parametrize("value", [None, "", "  ", "x\nname", "x" * 256])
def test_create_policy_rejects_invalid_name(app, value: object) -> None:
    with app.app_context():
        with pytest.raises(ValueError):
            create_policy(name=value, payload=PAYLOAD, administrator_id=1)


def test_policy_administration_rejects_unavailable_or_missing_administrator(
    app,
) -> None:
    with app.app_context():
        disabled = _administrator("locked")
        db.session.commit()
        with pytest.raises(PolicyAdministrationError):
            create_policy(
                name="Unavailable", payload=PAYLOAD, administrator_id=disabled.id
            )
        with pytest.raises(PolicyAdministrationError):
            create_policy(name="Missing", payload=PAYLOAD, administrator_id=99999)


def test_policy_administration_handles_missing_policy_and_lifecycle(app) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()
        with pytest.raises(PolicyAdministrationNotFound):
            add_revision(
                policy_uuid=uuid4(), payload=PAYLOAD, administrator_id=administrator.id
            )
        with pytest.raises(ValueError):
            set_lifecycle(policy_uuid=uuid4(), status="draft")
        with pytest.raises(PolicyAdministrationNotFound):
            set_lifecycle(policy_uuid=uuid4(), status="active")
        policy = Policy(policy_uuid=uuid4(), name="Lifecycle")
        db.session.add(policy)
        db.session.commit()
        assert set_lifecycle(
            policy_uuid=policy.policy_uuid, status="active"
        ).status == ("active")


def test_policy_administration_rolls_back_database_errors(app, monkeypatch) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()

        def fail_commit() -> None:
            raise SQLAlchemyError("forced test failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyAdministrationError):
            create_policy(
                name="Rollback", payload=PAYLOAD, administrator_id=administrator.id
            )


def test_policy_administration_maps_integrity_errors(app, monkeypatch) -> None:
    with app.app_context():
        administrator = _administrator()
        db.session.commit()

        def fail_commit() -> None:
            raise IntegrityError("statement", {}, None)

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyAdministrationConflict):
            create_policy(
                name="Conflict", payload=PAYLOAD, administrator_id=administrator.id
            )


def test_policy_administration_maps_revision_and_lifecycle_database_errors(
    app, monkeypatch
) -> None:
    with app.app_context():
        administrator = _administrator()
        policy = Policy(policy_uuid=uuid4(), name="Persistence")
        db.session.add(policy)
        db.session.commit()
        with pytest.raises(PolicyAdministrationError):
            add_revision(
                policy_uuid=policy.policy_uuid,
                payload=PAYLOAD,
                administrator_id=99999,
            )

        def fail_commit() -> None:
            raise SQLAlchemyError("forced test failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(PolicyAdministrationError):
            add_revision(
                policy_uuid=policy.policy_uuid,
                payload=PAYLOAD,
                administrator_id=administrator.id,
            )
        with pytest.raises(PolicyAdministrationError):
            set_lifecycle(policy_uuid=policy.policy_uuid, status="active")
