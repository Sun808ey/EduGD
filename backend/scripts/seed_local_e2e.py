"""Seed deterministic data for the disposable live browser test stack."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    Device,
    DeviceEnrollmentEvent,
    EnrollmentToken,
    Policy,
    PolicyRevision,
    policy_revision_content_hash,
    utc_now,
)
from app.services.administrator_authentication import bootstrap_administrator

ADMIN_USERNAME = "local.e2e.admin"
ADMIN_PASSWORD = "LocalE2EAdmin!2026"
READONLY_USERNAME = "local.e2e.reader"
READONLY_PASSWORD = "LocalE2EReader!2026"
OPERATOR_SUBJECT = "local:e2e"
REASON = "disposable live browser verification"
DEVICE_UUID = UUID("22222222-2222-4222-8222-222222222222")
POLICY_UUID = UUID("33333333-3333-4333-8333-333333333333")


def main() -> int:
    application = create_app("development")
    with application.app_context():
        if db.session.scalar(select(Administrator.id).limit(1)) is not None:
            raise RuntimeError("live E2E database must be empty before seeding")

        bootstrap_administrator(
            username=ADMIN_USERNAME,
            display_name="Local E2E Administrator",
            password=ADMIN_PASSWORD,
            operator_subject=OPERATOR_SUBJECT,
            reason=REASON,
        )
        administrator = db.session.scalar(
            select(Administrator).where(Administrator.username == ADMIN_USERNAME)
        )
        if administrator is None:
            raise RuntimeError("administrator bootstrap did not persist")

        readonly = Administrator(
            username=READONLY_USERNAME,
            display_name="Local E2E Reader",
            password_verifier=generate_password_hash(
                READONLY_PASSWORD, method="scrypt"
            ),
        )
        db.session.add(readonly)
        db.session.flush()
        db.session.add(
            AdministratorPermission(
                administrator_id=readonly.id,
                permission="policy.assign",
                granted_by_administrator_id=administrator.id,
                reason=REASON,
            )
        )
        db.session.add(
            AdministratorAuthenticationEvent(
                administrator_id=readonly.id,
                category="permission_granted",
                acting_administrator_id=administrator.id,
                reason=REASON,
            )
        )

        device = Device(
            device_uuid=DEVICE_UUID,
            android_version="14",
            api_level=34,
            status="active",
        )
        policy = Policy(
            policy_uuid=POLICY_UUID, name="Local E2E policy", status="active"
        )
        payload = {"schema_version": 1, "blocked_apps": ["org.example.blocked"]}
        revision = PolicyRevision(
            policy=policy,
            version=1,
            payload=payload,
            content_hash=policy_revision_content_hash(payload),
            created_by=str(administrator.administrator_uuid),
            created_by_administrator_id=administrator.id,
        )
        token = EnrollmentToken(
            verifier=b"e" * 32,
            pepper_version=1,
            status="active",
            expires_at=utc_now() + timedelta(minutes=10),
            issued_by=str(administrator.administrator_uuid),
            reason=REASON,
        )
        db.session.add_all([device, policy, revision, token])
        db.session.flush()
        db.session.add(
            DeviceEnrollmentEvent(
                device_id=device.id,
                category="token_issued",
                administrator_subject=str(administrator.administrator_uuid),
                reason=REASON,
            )
        )
        db.session.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
