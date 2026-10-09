"""Seed the disposable NDEJJE SS live-demo scenario.

This fixture is intentionally synthetic.  It exercises the complete admin read
path without claiming that the currently attached physical Android device has
been enrolled or identified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from uuid import UUID, uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDSA,
    SECP256R1,
    generate_private_key,
)
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    Device,
    DeviceAuditBatch,
    DeviceAuditChainHead,
    DeviceCheckIn,
    DeviceComplianceState,
    DeviceCredential,
    DeviceEnrollmentEvent,
    DeviceLocationAssignment,
    DevicePolicyAssignment,
    DevicePolicyState,
    DeviceRegistrationEvent,
    DeviceSecurityEvent,
    EnrollmentToken,
    Incident,
    Policy,
    PolicyApplicationEvent,
    PolicyAssignmentChainHead,
    PolicyAssignmentEvent,
    PolicyRevision,
    School,
    policy_revision_content_hash,
    utc_now,
)
from app.services.administrator_authentication import bootstrap_administrator

ADMIN_USERNAME = "local.e2e.admin"
ADMIN_PASSWORD = "LocalE2EAdmin!2026"
READONLY_USERNAME = "local.e2e.reader"
READONLY_PASSWORD = "LocalE2EReader!2026"
OPERATOR_SUBJECT = "local:e2e"
REASON = "NDEJJE SS local live-demo scenario"
DEVICE_UUID = UUID("22222222-2222-4222-8222-222222222222")
CLASS_POLICY_UUID = UUID("33333333-3333-4333-8333-333333333333")
EXAM_POLICY_UUID = UUID("44444444-4444-4444-8444-444444444444")


def _policy_payload(*, mode_id: str, kiosk: bool) -> dict[str, object]:
    controls = {
        "camera_disabled": kiosk,
        "screen_capture_disabled": kiosk,
        "unknown_sources_disabled": True,
        "factory_reset_disabled": True,
        "safe_boot_disabled": True,
        "add_users_disabled": True,
        "account_changes_disabled": True,
        "usb_file_transfer_disabled": True,
    }
    return {
        "schema_version": 3,
        "timezone": "Africa/Kampala",
        "refresh_after_seconds": 300,
        "default_mode": mode_id,
        "emergency_packages": ["org.edug.dpc"],
        "required_capabilities": ["screen_time", "web_filter"],
        "minimum_dpc_version": 3,
        "modes": [
            {
                "mode_id": mode_id,
                "application_mode": "allowlist",
                "allowed_packages": ["org.edug.dpc", "org.edug.exam"]
                if kiosk
                else ["org.edug.dpc"],
                "blocked_packages": [],
                "lock_task_packages": ["org.edug.exam"] if kiosk else [],
                "user_restrictions": [],
                "device_controls": controls,
            }
        ],
        "schedules": [],
        "screen_time": {
            "daily_limit_minutes": 120,
            "reset_minute": 0,
            "exhausted_mode_id": mode_id,
        },
        "web_filter": {
            "default_action": "allow",
            "rules": [
                {
                    "rule_id": "betting_domains",
                    "domain": "example.com.",
                    "include_subdomains": True,
                    "action": "block",
                    "reason": "protect learning time",
                }
            ],
        },
        "network_controls": {
            "wifi_only": True,
            "disallow_mobile_network_configuration": True,
            "disallow_tethering": True,
            "disallow_user_vpn": True,
            "always_on_filtering_vpn": True,
            "vpn_lockdown_required": True,
        },
        "telephony_controls": {
            "disallow_outgoing_calls": True,
            "disallow_sms": True,
            "preserve_emergency_calls": True,
        },
    }


def _hash_payload(value: object) -> bytes:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).digest()


def _create_policy(
    *,
    administrator: Administrator,
    name: str,
    policy_uuid: UUID,
    payload: dict[str, object],
) -> tuple[Policy, PolicyRevision]:
    policy = Policy(policy_uuid=policy_uuid, name=name, status="active")
    revision = PolicyRevision(
        policy=policy,
        version=1,
        payload=payload,
        content_hash=policy_revision_content_hash(payload),
        created_by=str(administrator.administrator_uuid),
        created_by_administrator_id=administrator.id,
    )
    db.session.add(policy)
    db.session.flush()
    return policy, revision


def _assignment_event_hash(
    *, device_id: int, operation: str, assignment_id: int, previous: bytes | None
) -> bytes:
    return _hash_payload(
        {
            "device_id": device_id,
            "operation": operation,
            "assignment_id": assignment_id,
            "previous_event_hash": previous.hex() if previous else None,
        }
    )


def _seed() -> None:
    if db.session.scalar(select(Administrator.id).limit(1)) is not None:
        raise RuntimeError("live demo database must be empty before seeding")

    bootstrap_administrator(
        username=ADMIN_USERNAME,
        display_name="NDEJJE SS Administrator",
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
        display_name="NDEJJE SS Read-only Reviewer",
        password_verifier=generate_password_hash(READONLY_PASSWORD, method="scrypt"),
    )
    db.session.add(readonly)
    db.session.flush()
    db.session.add_all(
        [
            AdministratorPermission(
                administrator_id=readonly.id,
                permission="policy.assign",
                granted_by_administrator_id=administrator.id,
                reason=REASON,
            ),
            AdministratorAuthenticationEvent(
                administrator_id=readonly.id,
                category="permission_granted",
                acting_administrator_id=administrator.id,
                reason=REASON,
            ),
            School(
                name="NDEJJE SS",
                district="Pending operator confirmation",
                school_type="Secondary",
                contact_person="ICT Master (demo)",
                official_telephone="+256 700 000 000",
                official_email="ict@ndejje-demo.invalid",
                physical_location="NDEJJE SS, Uganda (confirm exact location)",
                authorised_administrator_name="NDEJJE SS Administrator",
                registered_by_administrator_id=administrator.id,
            ),
        ]
    )

    now = utc_now()
    device = Device(
        device_uuid=DEVICE_UUID,
        android_version="14",
        api_level=34,
        status="active",
        asset_number="NDEJJE-SS-PHONE-001",
        manufacturer="Pending USB confirmation",
        model="Pending USB confirmation",
        serial_number="LOCAL-DEMO-SERIAL-PENDING",
        date_received=date.today(),
        condition="Good (synthetic demo)",
        department="ICT and Examinations",
        asset_lifecycle_status="in_use",
        asset_notes=(
            "LOCAL DEMO SIMULATION — physical USB metadata pending ADB authorization; "
            "replace before real enrollment."
        ),
        last_sync_at=now,
    )
    db.session.add(device)
    class_policy, class_revision = _create_policy(
        administrator=administrator,
        name="Class Time Policy",
        policy_uuid=CLASS_POLICY_UUID,
        payload=_policy_payload(mode_id="school", kiosk=False),
    )
    exam_policy, exam_revision = _create_policy(
        administrator=administrator,
        name="Exam Mode Policy",
        policy_uuid=EXAM_POLICY_UUID,
        payload=_policy_payload(mode_id="exam", kiosk=True),
    )
    db.session.flush()

    token = EnrollmentToken(
        verifier=b"d" * 32,
        pepper_version=1,
        bound_device_id=device.id,
        policy_revision_id=class_revision.id,
        status="consumed",
        expires_at=now + timedelta(minutes=10),
        consumed_at=now - timedelta(days=6),
        consumed_by_device_id=device.id,
        issued_by=str(administrator.administrator_uuid),
        reason=REASON,
    )
    db.session.add(token)
    db.session.flush()
    key = generate_private_key(SECP256R1())
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    credential = DeviceCredential(
        device_id=device.id,
        enrollment_token_id=token.id,
        algorithm="ECDSA_P256_SHA256",
        public_key_der=public_der,
        public_key_fingerprint=hashlib.sha256(public_der).digest(),
        status="active",
        issued_at=now - timedelta(days=6),
        last_used_at=now,
    )
    db.session.add(credential)
    db.session.flush()
    db.session.add_all(
        [
            DeviceRegistrationEvent(
                device_id=device.id,
                event_type="registered",
                stored_android_version="14",
                stored_api_level=34,
                reported_android_version="14",
                reported_api_level=34,
                created_at=now - timedelta(days=6),
            ),
            DeviceEnrollmentEvent(
                device_id=device.id,
                credential_id=credential.id,
                token_id=token.id,
                category="token_issued",
                administrator_subject=str(administrator.administrator_uuid),
                reason=REASON,
                created_at=now - timedelta(days=7),
            ),
            DeviceEnrollmentEvent(
                device_id=device.id,
                credential_id=credential.id,
                token_id=token.id,
                category="token_consumed",
                reason="Enrollment token consumed by the local demo device",
                public_key_fingerprint=credential.public_key_fingerprint,
                created_at=now - timedelta(days=6),
            ),
            DeviceEnrollmentEvent(
                device_id=device.id,
                credential_id=credential.id,
                token_id=token.id,
                category="enrollment_succeeded",
                reason="DPC enrollment completed in the local simulation",
                public_key_fingerprint=credential.public_key_fingerprint,
                created_at=now - timedelta(days=6),
            ),
            DeviceLocationAssignment(
                device_id=device.id,
                target_type="class",
                target_name="Senior Five",
                responsible_officer="ICT Master",
                assigned_at=(now - timedelta(days=5)).date(),
                issue_condition="Good",
                recorded_by_administrator_id=administrator.id,
            ),
        ]
    )
    db.session.flush()

    old_assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=class_revision.id,
        assigned_by_administrator_id=administrator.id,
        reason="Class Time Policy assigned after enrollment",
        status="superseded",
        assigned_at=now - timedelta(days=5),
        superseded_at=now - timedelta(days=1),
    )
    active_assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=exam_revision.id,
        assigned_by_administrator_id=administrator.id,
        reason="Exam Mode Policy assigned for the live demo",
        status="active",
        assigned_at=now - timedelta(hours=2),
    )
    db.session.add_all([old_assignment, active_assignment])
    db.session.flush()
    first_assignment_hash = _assignment_event_hash(
        device_id=device.id,
        operation="assign",
        assignment_id=old_assignment.id,
        previous=None,
    )
    second_assignment_hash = _assignment_event_hash(
        device_id=device.id,
        operation="replace",
        assignment_id=active_assignment.id,
        previous=first_assignment_hash,
    )
    db.session.add_all(
        [
            PolicyAssignmentEvent(
                device_id=device.id,
                assignment_id=old_assignment.id,
                administrator_id=administrator.id,
                operation="assign",
                reason=old_assignment.reason,
                previous_event_hash=None,
                event_hash=first_assignment_hash,
                created_at=old_assignment.assigned_at,
            ),
            PolicyAssignmentEvent(
                device_id=device.id,
                assignment_id=active_assignment.id,
                previous_assignment_id=old_assignment.id,
                administrator_id=administrator.id,
                operation="replace",
                reason=active_assignment.reason,
                previous_event_hash=first_assignment_hash,
                event_hash=second_assignment_hash,
                created_at=active_assignment.assigned_at,
            ),
            PolicyAssignmentChainHead(
                device_id=device.id,
                head_event_hash=second_assignment_hash,
                updated_at=now,
            ),
        ]
    )

    check_in = DeviceCheckIn(
        check_in_uuid=uuid4(),
        device_id=device.id,
        credential_id=credential.id,
        observed_at=now,
        elapsed_realtime_ms=86400000,
        boot_count=3,
        dpc_version=3,
        android_version="14",
        api_level=34,
        security_patch=date.today(),
        capabilities=["screen_time", "web_filter", "network_controls"],
        current_policy_uuid=EXAM_POLICY_UUID,
        current_revision_uuid=exam_revision.revision_uuid,
        policy_status="applied",
        enforcement_healthy=True,
        queued_event_count=0,
        content_hash=b"k" * 32,
    )
    db.session.add(check_in)
    db.session.flush()
    db.session.add_all(
        [
            DeviceComplianceState(
                device_id=device.id,
                last_check_in_id=check_in.id,
                last_observed_at=check_in.observed_at,
                last_received_at=now,
                last_boot_count=check_in.boot_count,
                dpc_version=check_in.dpc_version,
                android_version=check_in.android_version,
                api_level=check_in.api_level,
                security_patch=check_in.security_patch,
                capabilities=check_in.capabilities,
                current_policy_uuid=check_in.current_policy_uuid,
                current_revision_uuid=check_in.current_revision_uuid,
                policy_status=check_in.policy_status,
                enforcement_healthy=True,
                queued_event_count=0,
            ),
        ]
    )
    class_application = PolicyApplicationEvent(
        acknowledgement_uuid=uuid4(),
        device_id=device.id,
        credential_id=credential.id,
        observed_at=now - timedelta(hours=3),
        elapsed_realtime_ms=86000000,
        boot_count=3,
        policy_uuid=CLASS_POLICY_UUID,
        revision_uuid=class_revision.revision_uuid,
        outcome="applied",
        content_hash=class_revision.content_hash,
    )
    exam_application = PolicyApplicationEvent(
        acknowledgement_uuid=uuid4(),
        device_id=device.id,
        credential_id=credential.id,
        observed_at=now - timedelta(hours=2),
        elapsed_realtime_ms=86400000,
        boot_count=3,
        policy_uuid=EXAM_POLICY_UUID,
        revision_uuid=exam_revision.revision_uuid,
        outcome="applied",
        content_hash=exam_revision.content_hash,
    )
    db.session.add_all([class_application, exam_application])
    db.session.flush()
    db.session.add(
        DevicePolicyState(
            device_id=device.id,
            last_event_id=exam_application.id,
            policy_uuid=EXAM_POLICY_UUID,
            revision_uuid=exam_revision.revision_uuid,
            outcome="applied",
            observed_at=exam_application.observed_at,
            received_at=now,
        )
    )

    event_specs = [
        (
            "policy_block",
            "blocked_social_app",
            {
                "package_name": "com.zhiliaoapp.musically",
                "message": "TikTok blocked during Class Time Policy",
            },
        ),
        ("web_filter_blocked", "betting_domains", {"domain_hash": "a" * 64}),
        (
            "tamper_attempt",
            "exam_kiosk_exit",
            {"attempt": "leave_exam_app", "message": "Attempted to leave exam app"},
        ),
        (
            "configuration_changed",
            "block_wifi_changes",
            {"setting": "wifi", "message": "Wi-Fi settings change blocked"},
        ),
        (
            "policy_block",
            "screenshot_disabled",
            {
                "setting": "screenshot",
                "message": "Screenshot attempt blocked in Exam Mode",
            },
        ),
    ]
    previous_event_hash: bytes | None = None
    event_rows: list[DeviceSecurityEvent] = []
    for sequence, (event_code, rule_id, metadata) in enumerate(event_specs, start=1):
        event_hash = _hash_payload(
            {
                "device_uuid": str(device.device_uuid),
                "sequence": sequence,
                "event_code": event_code,
                "rule_id": rule_id,
                "metadata": metadata,
                "previous_event_hash": previous_event_hash.hex()
                if previous_event_hash
                else None,
            }
        )
        event_rows.append(
            DeviceSecurityEvent(
                event_uuid=uuid4(),
                batch_id=0,
                device_id=device.id,
                sequence=sequence,
                occurred_at=now - timedelta(minutes=25 - sequence * 3),
                elapsed_realtime_ms=86400000 + sequence * 1000,
                boot_count=3,
                event_code=event_code,
                outcome="detected" if event_code == "tamper_attempt" else "blocked",
                policy_uuid=CLASS_POLICY_UUID if sequence <= 2 else EXAM_POLICY_UUID,
                revision_uuid=class_revision.revision_uuid
                if sequence <= 2
                else exam_revision.revision_uuid,
                rule_id=rule_id,
                event_metadata=metadata,
                previous_event_hash=previous_event_hash,
                event_hash=event_hash,
                received_at=now,
            )
        )
        previous_event_hash = event_hash
    batch = DeviceAuditBatch(
        batch_uuid=uuid4(),
        device_id=device.id,
        credential_id=credential.id,
        first_sequence=1,
        last_sequence=len(event_rows),
        previous_head=None,
        final_head=previous_event_hash,
        signature_algorithm="ECDSA_P256_SHA256",
        signature=key.sign(b"local-demo-audit-batch", ECDSA(hashes.SHA256())),
        content_hash=b"b" * 32,
        received_at=now,
    )
    db.session.add(batch)
    db.session.flush()
    for row in event_rows:
        row.batch_id = batch.id
    db.session.add_all(event_rows)
    db.session.add(
        DeviceAuditChainHead(
            device_id=device.id,
            last_sequence=len(event_rows),
            head_event_hash=previous_event_hash,
            updated_at=now,
        )
    )
    db.session.add_all(
        [
            Incident(
                incident_number="NDEJJE-INC-001",
                device_id=device.id,
                incident_type="unauthorised_application",
                description="Blocked social application launch recorded during Class Time Policy.",
                reported_by="EDUGD DPC (local simulation)",
                status="OPEN",
                responsible_person="ICT Master",
                created_by_administrator_id=administrator.id,
            ),
            Incident(
                incident_number="NDEJJE-INC-002",
                device_id=device.id,
                incident_type="kiosk_bypass_attempt",
                description="Exam Mode kiosk exit attempt requires review.",
                reported_by="EDUGD DPC (local simulation)",
                status="OPEN",
                responsible_person="ICT Master",
                created_by_administrator_id=administrator.id,
            ),
        ]
    )
    db.session.commit()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed the disposable NDEJJE SS demo scenario"
    )
    parser.parse_args()
    application = create_app("development")
    with application.app_context():
        _seed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
