"""Seed the disposable NDEJJE SS operational scenario.

The fixture uses deterministic school-owned asset records and privacy-limited
device evidence so the complete administrator workflow can be exercised on the
disposable local stack without using hosted resources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from random import Random
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
    DeviceAssetChangeEvent,
    DeviceAuditBatch,
    DeviceAuditChainHead,
    DeviceBlockOverride,
    DeviceCheckIn,
    DeviceComplianceState,
    DeviceControlEvent,
    DeviceCredential,
    DeviceEnrollmentEvent,
    DeviceLocationAssignment,
    DevicePolicyAssignment,
    DevicePolicyState,
    DeviceRegistrationEvent,
    DeviceSecurityEvent,
    DeviceUsageDaily,
    DeviceWebFilterEvent,
    EnrollmentToken,
    Incident,
    ManagedApplication,
    ManagedDomain,
    Policy,
    PolicyApplicationEvent,
    PolicyAssignmentChainHead,
    PolicyAssignmentEvent,
    PolicyRevision,
    PolicySynchronizationChainHead,
    PolicySynchronizationEvent,
    School,
    policy_revision_content_hash,
)
from app.services.administrator_authentication import bootstrap_administrator

ADMIN_USERNAME = os.getenv("EDUG_DEMO_ADMIN_USERNAME", "ed.admin")
READONLY_USERNAME = os.getenv("EDUG_DEMO_READONLY_USERNAME", "local.e2e.reader")


def _required_demo_credential(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} must be set when running the disposable local demo seeder"
        )
    return value


ADMIN_PASSWORD = _required_demo_credential("EDUG_DEMO_ADMIN_PASSWORD")
READONLY_PASSWORD = _required_demo_credential("EDUG_DEMO_READONLY_PASSWORD")
OPERATOR_SUBJECT = "local:e2e"
REASON = "NDEJJE SS operational scenario"
PHONE_UUID = UUID("22222222-2222-4222-8222-222222222222")
TABLET_UUID = UUID("55555555-5555-4555-8555-555555555555")
CLASS_POLICY_UUID = UUID("33333333-3333-4333-8333-333333333333")
EXAM_POLICY_UUID = UUID("44444444-4444-4444-8444-444444444444")
DPC_PACKAGE = "io.github.sun808ey.edugd.dpc"
EXAM_PACKAGE = "org.edug.exam"
DEMO_PERIOD_START = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
DEMO_PERIOD_END = datetime(2026, 10, 21, 15, 45, tzinfo=UTC)
_DEMO_RANDOM = Random(20261021)


def _demo_timestamp(
    *, days_ago: int = 0, hours_ago: int = 0, minutes_ago: int = 0
) -> datetime:
    """Return a deterministic but naturally varied local-demo timestamp.

    The fixture is synthetic and intentionally reproducible. Small per-record
    offsets avoid a machine-generated wall of identical timestamps while the
    fixed October window keeps screenshots and E2E assertions stable.
    """
    base = DEMO_PERIOD_END - timedelta(
        days=days_ago, hours=hours_ago, minutes=minutes_ago
    )
    jitter = timedelta(
        minutes=_DEMO_RANDOM.randint(3, 27),
        seconds=_DEMO_RANDOM.randint(0, 59),
    )
    timestamp = base - jitter
    if timestamp < DEMO_PERIOD_START:
        return DEMO_PERIOD_START + timedelta(
            minutes=_DEMO_RANDOM.randint(0, 45),
            seconds=_DEMO_RANDOM.randint(0, 59),
        )
    return timestamp


BLOCKED_APPLICATIONS = [
    ("TikTok", "com.zhiliaoapp.musically", "social"),
    ("Instagram", "com.instagram.android", "social"),
    ("X", "com.twitter.android", "social"),
    ("WhatsApp", "com.whatsapp", "social"),
    ("Facebook", "com.facebook.katana", "social"),
    ("Snapchat", "com.snapchat.android", "social"),
    ("Reddit", "com.reddit.frontpage", "social"),
    ("LinkedIn", "com.linkedin.android", "social"),
    ("PUBG Mobile", "com.tencent.ig", "games"),
    ("Call of Duty: Mobile", "com.activision.callofduty.shooter", "games"),
    ("Subway Surfers", "com.kiloo.subwaysurf", "games"),
    ("Free Fire", "com.dts.freefireth", "games"),
    ("Candy Crush Saga", "com.king.candycrushsaga", "games"),
    ("EA Sports FC Mobile", "com.ea.gp.fifamobile", "games"),
    ("Roblox", "com.roblox.client", "games"),
    ("Minecraft", "com.mojang.minecraftpe", "games"),
    ("1xBet", "com.xbet.client", "betting"),
    ("Bet365", "com.bet365", "betting"),
    ("DraftKings", "com.draftkings.sportsbook", "betting"),
    ("Betway", "com.betway.betway", "betting"),
    ("FanDuel", "com.fanduel.android", "betting"),
    ("SportyBet", "com.sportybet.android", "betting"),
    ("Netflix", "com.netflix.mediaclient", "entertainment"),
    ("Spotify", "com.spotify.music", "entertainment"),
    ("Twitch", "tv.twitch.android.app", "entertainment"),
    ("Disney+", "com.disney.disneyplus", "entertainment"),
    ("Amazon Prime Video", "com.amazon.avod.thirdpartyclient", "entertainment"),
]
ALLOWED_APPLICATIONS = [
    ("Duolingo", "com.duolingo", "education"),
    ("Khan Academy", "org.khanacademy.android", "education"),
    ("Coursera", "org.coursera.android", "education"),
    ("Quizlet", "com.quizlet.android", "education"),
    ("Photomath", "com.microblink.photomath", "education"),
    ("edX", "org.edx.mobile", "education"),
    ("SoloLearn", "com.sololearn", "education"),
    ("Udemy", "com.udemy.android", "education"),
    ("Brilliant", "org.brilliant.android", "education"),
    ("LinkedIn Learning", "com.linkedin.android.learning", "education"),
]
BLOCKED_DOMAINS = [
    ("x.com", "social"),
    ("whatsapp.com", "social"),
    ("netflix.com", "entertainment"),
    ("spotify.com", "entertainment"),
    ("pubgmobile.com", "games"),
    ("betway.com", "betting"),
]


def _policy_payload(*, mode_id: str, kiosk: bool) -> dict[str, object]:
    learning_packages = [package for _, package, _ in ALLOWED_APPLICATIONS]
    allowed_packages = [DPC_PACKAGE, *learning_packages]
    if kiosk:
        allowed_packages.append(EXAM_PACKAGE)
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
        "policy_code": "EXAMINATION_DEVICE" if kiosk else "LEARNING_DEVICE",
        "description": (
            "Controls the school-owned phone during Senior Five examinations. "
            "Only the examination workflow and the EduGD controller remain available."
            if kiosk
            else "Controls the shared school tablet during Computer Studies lessons. "
            "Only verified learning applications remain available."
        ),
        "timezone": "Africa/Kampala",
        "refresh_after_seconds": 300,
        "default_mode": mode_id,
        "emergency_packages": [DPC_PACKAGE],
        "required_capabilities": [
            "screen_time",
            "web_filter",
            "app_visibility",
            "application_restrictions",
            "device_restrictions",
            "network_settings",
            "screen_lock",
        ],
        "minimum_dpc_version": 3,
        "modes": [
            {
                "mode_id": mode_id,
                "application_mode": "allowlist",
                "allowed_packages": sorted(set(allowed_packages)),
                "blocked_packages": sorted(
                    package for _, package, _ in BLOCKED_APPLICATIONS
                ),
                "lock_task_packages": [EXAM_PACKAGE] if kiosk else [],
                "user_restrictions": [],
                "device_controls": controls,
            }
        ],
        "schedules": [
            {
                "schedule_id": "weekday_exam_mode" if kiosk else "weekday_class_time",
                "days": [1, 2, 3, 4, 5],
                "start_minute": 480,
                "end_minute": 960,
                "mode_id": mode_id,
                "priority": 1,
            }
        ],
        "screen_time": {
            "daily_limit_minutes": 120,
            "reset_minute": 0,
            "exhausted_mode_id": mode_id,
        },
        "web_filter": {
            "default_action": "allow",
            "rules": [
                {
                    "rule_id": f"default_blocked_domain_{index}",
                    "domain": domain,
                    "include_subdomains": True,
                    "action": "block",
                    "reason": "Restricted domain blocked by the default school compliance policy.",
                }
                for index, (domain, _category) in enumerate(BLOCKED_DOMAINS, start=1)
            ],
        },
        "network_controls": {
            "wifi_only": False,
            "disallow_mobile_network_configuration": False,
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
        "device_use": {
            "mode": "examination" if kiosk else "dedicated_learning",
            "kiosk_mode_enabled": False,
            "display_school_name": True,
            "school_name": None,
            "support_message": "Contact HOD COMPUTER STUDIES at the ICT office.",
        },
        "application_controls": {
            "allow_installation_of_other_applications": False,
            "allow_installation_from_unknown_sources": False,
            "allow_uninstall_of_approved_applications": False,
            "allow_disable_of_approved_applications": False,
            "allow_google_play_store": False,
            "allow_file_sharing_applications": False,
            "file_sharing_packages": [],
        },
        "device_restrictions": {
            "block_factory_reset": True,
            "block_safe_mode": True,
            "block_developer_options_and_debugging": True,
            "block_usb_file_transfer": True,
            "block_account_changes": True,
            "block_user_switching": True,
            "block_network_reset": True,
            "block_wifi_changes": False,
            "disable_screenshots": kiosk,
            "disable_screen_recording": kiosk,
            "disable_camera": kiosk,
            "disable_microphone": kiosk,
            "disable_location": True,
        },
        "screen_lock": {
            "require_screen_lock": True,
            "automatic_lock_after_minutes": 5,
            "allow_biometric_unlock": False,
            "allow_learner_change_lock_method": False,
        },
        "network_settings": {
            "allow_wifi": True,
            "allow_mobile_data": True,
            "allow_bluetooth": False,
            "allow_hotspot_creation": False,
            "allow_vpn_changes": False,
            "allow_network_reset": False,
        },
        "compliance_settings": {
            "device_enrolled": True,
            "dpc_active": True,
            "policy_version_current": True,
            "approved_learning_application_installed": True,
            "kiosk_mode_active": False,
            "unknown_sources_blocked": True,
            "factory_reset_restriction_active": True,
            "required_restrictions_applied": True,
            "connection_review_after_days": 3,
        },
        "offline_settings": {
            "enforce_last_valid_policy_offline": True,
            "store_local_policy_copy": True,
            "queue_events_while_offline": True,
            "apply_policy_changes_after_reconnection": True,
            "expire_policy_when_offline": False,
        },
        "administrator_notes": (
            "Use this record to explain the school-facing controls in plain language.\n"
            "Restricted applications and betting domains are blocked, the last valid policy stays active offline, "
            "and only administrative device evidence is retained."
        ),
        "data_collection_settings": {
            "store_device_asset_number": True,
            "store_device_policy_version": True,
            "store_last_synchronisation_time": True,
            "store_compliance_result": True,
            "store_administrative_actions": True,
            "collect_learner_location": False,
            "read_private_messages": False,
            "read_photographs": False,
            "record_microphone": False,
            "store_browsing_history": False,
        },
    }


def _hash_payload(value: object) -> bytes:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).digest()


def _domain_hash(domain: str) -> str:
    """Return the same lowercase SHA-256 representation used by DPC evidence."""
    return hashlib.sha256(domain.encode("utf-8")).hexdigest()


def _create_policy(
    *,
    administrator: Administrator,
    name: str,
    policy_uuid: UUID,
    payload: dict[str, object],
) -> tuple[Policy, PolicyRevision]:
    policy_created_at = _demo_timestamp(days_ago=17 if "Class" in name else 15)
    policy = Policy(
        policy_uuid=policy_uuid,
        name=name,
        status="active",
        created_at=policy_created_at,
        updated_at=_demo_timestamp(days_ago=2),
    )
    revision = PolicyRevision(
        policy=policy,
        version=1,
        payload=payload,
        content_hash=policy_revision_content_hash(payload),
        created_by=str(administrator.administrator_uuid),
        created_by_administrator_id=administrator.id,
        created_at=policy_created_at,
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


def _seed_tablet_operations(
    *,
    tablet: Device,
    administrator: Administrator,
    policy: Policy,
    revision: PolicyRevision,
) -> None:
    """Add the tablet's October enrollment, policy, sync and evidence trail."""
    token_created = _demo_timestamp(days_ago=18, hours_ago=2)
    token = EnrollmentToken(
        verifier=b"t" * 32,
        pepper_version=1,
        bound_device_id=tablet.id,
        policy_revision_id=revision.id,
        status="consumed",
        expires_at=token_created + timedelta(minutes=10),
        consumed_at=token_created + timedelta(minutes=4),
        consumed_by_device_id=tablet.id,
        issued_by=str(administrator.administrator_uuid),
        reason="Tablet enrollment for Computer Studies",
        created_at=token_created,
    )
    db.session.add(token)
    db.session.flush()

    key = generate_private_key(SECP256R1())
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    credential = DeviceCredential(
        device_id=tablet.id,
        enrollment_token_id=token.id,
        algorithm="ECDSA_P256_SHA256",
        public_key_der=public_der,
        public_key_fingerprint=hashlib.sha256(public_der).digest(),
        status="active",
        issued_at=token_created + timedelta(minutes=4),
        last_used_at=_demo_timestamp(hours_ago=5),
    )
    db.session.add(credential)
    db.session.flush()
    db.session.add_all(
        [
            DeviceRegistrationEvent(
                device_id=tablet.id,
                event_type="registered",
                stored_android_version="14",
                stored_api_level=34,
                reported_android_version="14",
                reported_api_level=34,
                created_at=token_created,
            ),
            DeviceEnrollmentEvent(
                device_id=tablet.id,
                credential_id=credential.id,
                token_id=token.id,
                category="token_issued",
                administrator_subject=str(administrator.administrator_uuid),
                reason="Enrollment token issued for the Computer Studies tablet",
                created_at=token_created,
            ),
            DeviceEnrollmentEvent(
                device_id=tablet.id,
                credential_id=credential.id,
                token_id=token.id,
                category="token_consumed",
                reason="Enrollment token consumed by the enrolled tablet",
                public_key_fingerprint=credential.public_key_fingerprint,
                created_at=token_created + timedelta(minutes=4),
            ),
            DeviceEnrollmentEvent(
                device_id=tablet.id,
                credential_id=credential.id,
                token_id=token.id,
                category="enrollment_succeeded",
                reason="Device-owner enrollment completed",
                public_key_fingerprint=credential.public_key_fingerprint,
                created_at=token_created + timedelta(minutes=5),
            ),
            DeviceLocationAssignment(
                device_id=tablet.id,
                target_type="class",
                target_name="Senior Four",
                responsible_officer="HOD COMPUTER STUDIES",
                assigned_at=_demo_timestamp(days_ago=17).date(),
                issue_condition="Good",
                recorded_by_administrator_id=administrator.id,
            ),
        ]
    )
    db.session.flush()

    assignment = DevicePolicyAssignment(
        device_id=tablet.id,
        policy_revision_id=revision.id,
        assigned_by_administrator_id=administrator.id,
        reason="Learning Device Policy assigned to the Computer Studies tablet",
        status="active",
        assigned_at=_demo_timestamp(days_ago=16),
    )
    db.session.add(assignment)
    db.session.flush()
    assignment_hash = _assignment_event_hash(
        device_id=tablet.id,
        operation="assign",
        assignment_id=assignment.id,
        previous=None,
    )
    db.session.add_all(
        [
            PolicyAssignmentEvent(
                device_id=tablet.id,
                assignment_id=assignment.id,
                administrator_id=administrator.id,
                operation="assign",
                reason=assignment.reason,
                previous_event_hash=None,
                event_hash=assignment_hash,
                created_at=assignment.assigned_at,
            ),
            PolicyAssignmentChainHead(
                device_id=tablet.id,
                head_event_hash=assignment_hash,
                updated_at=_demo_timestamp(days_ago=16, hours_ago=1),
            ),
        ]
    )

    check_in = DeviceCheckIn(
        check_in_uuid=uuid4(),
        device_id=tablet.id,
        credential_id=credential.id,
        observed_at=_demo_timestamp(hours_ago=5),
        elapsed_realtime_ms=490000000,
        boot_count=7,
        dpc_version=3,
        android_version="14",
        api_level=34,
        security_patch=_demo_timestamp(days_ago=3).date(),
        capabilities=["screen_time", "web_filter", "network_controls"],
        current_policy_uuid=policy.policy_uuid,
        current_revision_uuid=revision.revision_uuid,
        policy_status="applied",
        enforcement_healthy=True,
        queued_event_count=0,
        content_hash=hashlib.sha256(b"tablet-check-in").digest(),
        received_at=_demo_timestamp(hours_ago=5),
    )
    db.session.add(check_in)
    db.session.flush()
    db.session.add(
        DeviceComplianceState(
            device_id=tablet.id,
            last_check_in_id=check_in.id,
            last_observed_at=check_in.observed_at,
            last_received_at=check_in.received_at,
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
        )
    )
    application = PolicyApplicationEvent(
        acknowledgement_uuid=uuid4(),
        device_id=tablet.id,
        credential_id=credential.id,
        observed_at=_demo_timestamp(hours_ago=5),
        elapsed_realtime_ms=490000000,
        boot_count=7,
        policy_uuid=policy.policy_uuid,
        revision_uuid=revision.revision_uuid,
        outcome="applied",
        content_hash=revision.content_hash,
        received_at=_demo_timestamp(hours_ago=5),
    )
    db.session.add(application)
    db.session.flush()
    db.session.add(
        DevicePolicyState(
            device_id=tablet.id,
            last_event_id=application.id,
            policy_uuid=policy.policy_uuid,
            revision_uuid=revision.revision_uuid,
            outcome="applied",
            observed_at=application.observed_at,
            received_at=application.received_at,
        )
    )

    pseudonym = hashlib.sha256(str(tablet.device_uuid).encode()).digest()
    previous_sync: bytes | None = None
    for index, operation in enumerate(
        (
            "apply",
            "no_change",
            "apply",
            "no_change",
            "apply",
            "no_change",
            "apply",
            "no_change",
            "apply",
            "no_change",
            "apply",
        ),
        start=1,
    ):
        event_hash = _hash_payload(
            {
                "device": str(tablet.device_uuid),
                "sequence": index,
                "operation": operation,
                "previous": previous_sync.hex() if previous_sync else None,
            }
        )
        db.session.add(
            PolicySynchronizationEvent(
                device_id=tablet.id,
                credential_id=credential.id,
                requested_device_pseudonym=pseudonym,
                reported_client_version=index - 1,
                reported_policy_uuid=policy.policy_uuid,
                reported_revision_uuid=revision.revision_uuid,
                server_policy_version=revision.version,
                operation=operation,
                outcome_category="success",
                requested_at=_demo_timestamp(days_ago=index - 1, hours_ago=1),
                previous_event_hash=previous_sync,
                event_hash=event_hash,
            )
        )
        previous_sync = event_hash
    db.session.add(
        PolicySynchronizationChainHead(
            requested_device_pseudonym=pseudonym,
            head_event_hash=previous_sync,
            updated_at=_demo_timestamp(hours_ago=1),
        )
    )

    for day, minutes in enumerate(
        (58, 42, 55, 63, 48, 71, 46, 67, 52, 61, 39), start=0
    ):
        db.session.add(
            DeviceUsageDaily(
                device_id=tablet.id,
                usage_date=_demo_timestamp(days_ago=day).date(),
                active_minutes=minutes,
                policy_uuid=policy.policy_uuid,
                revision_uuid=revision.revision_uuid,
                reported_at=_demo_timestamp(days_ago=day, hours_ago=2),
            )
        )
    db.session.add(
        DeviceWebFilterEvent(
            device_id=tablet.id,
            domain_hash=hashlib.sha256(b"betway.com").digest(),
            rule_id="restricted-entertainment-domains",
            policy_uuid=policy.policy_uuid,
            revision_uuid=revision.revision_uuid,
            observed_at=_demo_timestamp(days_ago=2, hours_ago=3),
            received_at=_demo_timestamp(days_ago=2, hours_ago=3),
        )
    )

    event_specs = [
        (
            "web_filter_blocked",
            "restricted-entertainment-domains",
            {"domain_hash": _domain_hash("betway.com")},
        ),
        ("policy_block", "blocked_application", {"package_name": "com.roblox.client"}),
        ("configuration_changed", "unknown_sources", {"setting": "unknown_sources"}),
        (
            "policy_block",
            "blocked_application",
            {"package_name": "com.facebook.katana"},
        ),
        (
            "web_filter_blocked",
            "restricted-entertainment-domains",
            {"domain_hash": _domain_hash("1xbet.com")},
        ),
        ("configuration_changed", "network_settings", {"setting": "mobile_network"}),
        (
            "policy_block",
            "blocked_application",
            {"package_name": "com.activision.callofduty.shooter"},
        ),
        (
            "web_filter_blocked",
            "restricted-entertainment-domains",
            {"domain_hash": _domain_hash("sportybet.com")},
        ),
        ("policy_block", "blocked_application", {"package_name": "com.spotify.music"}),
        ("configuration_changed", "unknown_sources", {"setting": "unknown_sources"}),
        (
            "web_filter_blocked",
            "restricted-entertainment-domains",
            {"domain_hash": _domain_hash("bet365.com")},
        ),
    ]
    previous_event_hash: bytes | None = None
    event_rows: list[DeviceSecurityEvent] = []
    for sequence, (event_code, rule_id, metadata) in enumerate(event_specs, start=1):
        event_hash = _hash_payload(
            {
                "device_uuid": str(tablet.device_uuid),
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
                device_id=tablet.id,
                sequence=sequence,
                occurred_at=_demo_timestamp(days_ago=10 + sequence, hours_ago=2),
                elapsed_realtime_ms=490000000 + sequence * 1000,
                boot_count=7,
                event_code=event_code,
                outcome="blocked",
                policy_uuid=policy.policy_uuid,
                revision_uuid=revision.revision_uuid,
                rule_id=rule_id,
                event_metadata=metadata,
                previous_event_hash=previous_event_hash,
                event_hash=event_hash,
                received_at=_demo_timestamp(days_ago=10 + sequence, hours_ago=2),
            )
        )
        previous_event_hash = event_hash
    batch = DeviceAuditBatch(
        batch_uuid=uuid4(),
        device_id=tablet.id,
        credential_id=credential.id,
        first_sequence=1,
        last_sequence=len(event_rows),
        previous_head=None,
        final_head=previous_event_hash,
        signature_algorithm="ECDSA_P256_SHA256",
        signature=key.sign(b"tablet-audit-batch", ECDSA(hashes.SHA256())),
        content_hash=hashlib.sha256(b"tablet-audit-content").digest(),
        received_at=_demo_timestamp(days_ago=1),
    )
    db.session.add(batch)
    db.session.flush()
    for row in event_rows:
        row.batch_id = batch.id
    db.session.add_all(event_rows)
    db.session.add(
        DeviceAuditChainHead(
            device_id=tablet.id,
            last_sequence=len(event_rows),
            head_event_hash=previous_event_hash,
            updated_at=_demo_timestamp(days_ago=1, hours_ago=1),
        )
    )
    db.session.add(
        Incident(
            incident_number="NDEJJE-INC-003",
            device_id=tablet.id,
            incident_type="unauthorised_application",
            description="Restricted application launch blocked during a Computer Studies session.",
            reported_by="EDUGD DPC",
            status="ACTION_TAKEN",
            action_taken="Policy remained enforced and the event was reviewed.",
            responsible_person="HOD COMPUTER STUDIES",
            created_by_administrator_id=administrator.id,
            reported_at=_demo_timestamp(days_ago=2, hours_ago=3),
            created_at=_demo_timestamp(days_ago=2, hours_ago=4),
            updated_at=_demo_timestamp(days_ago=1, hours_ago=1),
        )
    )


def _seed(*, blank_school: bool = False) -> None:
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
    administrator.created_at = _demo_timestamp(days_ago=20, hours_ago=5)
    administrator.updated_at = _demo_timestamp(days_ago=1, hours_ago=3)
    administrator.password_changed_at = _demo_timestamp(days_ago=20, hours_ago=4)
    bootstrap_event = db.session.scalar(
        select(AdministratorAuthenticationEvent).where(
            AdministratorAuthenticationEvent.category == "bootstrap"
        )
    )
    if bootstrap_event is not None:
        bootstrap_event.created_at = _demo_timestamp(days_ago=20, hours_ago=5)
    readonly = Administrator(
        username=READONLY_USERNAME,
        display_name="NDEJJE SS Read-only Reviewer",
        password_verifier=generate_password_hash(READONLY_PASSWORD, method="scrypt"),
        created_at=_demo_timestamp(days_ago=19),
        updated_at=_demo_timestamp(days_ago=2),
        password_changed_at=_demo_timestamp(days_ago=19, hours_ago=1),
    )
    db.session.add(readonly)
    db.session.flush()
    initial_records: list[object] = [
        AdministratorPermission(
            administrator_id=readonly.id,
            permission="policy.assign",
            granted_by_administrator_id=administrator.id,
            reason=REASON,
            granted_at=_demo_timestamp(days_ago=19, hours_ago=2),
        ),
        AdministratorAuthenticationEvent(
            administrator_id=readonly.id,
            category="permission_granted",
            acting_administrator_id=administrator.id,
            reason=REASON,
            created_at=_demo_timestamp(days_ago=20, hours_ago=4),
        ),
    ]
    if not blank_school:
        initial_records.append(
            School(
                name="NDEJJE SS",
                district="BOMBO",
                school_type="SECONDARY",
                contact_person="HOD COMPUTER STUDIES",
                official_telephone="0703565376",
                official_email=None,
                physical_location="ABAITA",
                authorised_administrator_name="BOB",
                timezone="Africa/Kampala",
                registered_by_administrator_id=administrator.id,
            )
        )
    db.session.add_all(initial_records)

    now = DEMO_PERIOD_END
    phone = Device(
        device_uuid=PHONE_UUID,
        android_version="14",
        api_level=34,
        status="active",
        registered_at=_demo_timestamp(days_ago=20, hours_ago=4),
        created_at=_demo_timestamp(days_ago=20, hours_ago=5),
        updated_at=_demo_timestamp(days_ago=1),
        asset_number="NDEJJE-SS-PHONE-001",
        manufacturer="Google",
        model="Pixel 8 (Phone)",
        serial_number="NDEJJE-P8-001",
        date_received=_demo_timestamp(days_ago=20).date(),
        condition="Good",
        department="ICT and Examinations",
        asset_lifecycle_status="ENROLLED",
        asset_notes="School-owned phone assigned to Senior Five examinations.",
        last_sync_at=_demo_timestamp(hours_ago=2),
    )
    tablet = Device(
        device_uuid=TABLET_UUID,
        android_version="14",
        api_level=34,
        status="active",
        registered_at=_demo_timestamp(days_ago=18, hours_ago=4),
        created_at=_demo_timestamp(days_ago=18, hours_ago=5),
        updated_at=_demo_timestamp(days_ago=1, hours_ago=2),
        asset_number="NDEJJE-SS-TABLET-001",
        manufacturer="Google",
        model="Pixel Tablet (Medium tablet)",
        serial_number="NDEJJE-PT-001",
        date_received=_demo_timestamp(days_ago=18).date(),
        condition="Good",
        department="Computer Studies",
        asset_lifecycle_status="ASSIGNED",
        asset_notes="Shared learning tablet assigned to Senior Four Computer Studies.",
        last_sync_at=_demo_timestamp(hours_ago=5),
    )
    db.session.add_all([phone, tablet])

    db.session.add_all(
        [
            ManagedApplication(
                display_name=name,
                package_name=package,
                signing_certificate_sha256=hashlib.sha256(
                    f"NDEJJE:{package}".encode()
                ).digest(),
                category=category,
                education_approved=False,
                mandatory_block=True,
                status="enabled",
                created_at=_demo_timestamp(days_ago=17),
                updated_at=_demo_timestamp(days_ago=3),
            )
            for name, package, category in BLOCKED_APPLICATIONS
        ]
        + [
            ManagedApplication(
                display_name=name,
                package_name=package,
                signing_certificate_sha256=hashlib.sha256(
                    f"NDEJJE:{package}".encode()
                ).digest(),
                category=category,
                education_approved=True,
                mandatory_block=False,
                status="enabled",
                created_at=_demo_timestamp(days_ago=16),
                updated_at=_demo_timestamp(days_ago=3),
            )
            for name, package, category in ALLOWED_APPLICATIONS
        ]
    )
    db.session.add_all(
        ManagedDomain(
            domain=domain,
            category=category,
            status="enabled",
            created_at=_demo_timestamp(days_ago=16),
            updated_at=_demo_timestamp(days_ago=2),
        )
        for domain, category in [
            *BLOCKED_DOMAINS,
            ("khanacademy.org", "education"),
            ("duolingo.com", "education"),
        ]
    )
    # Keep the established evidence construction focused on the phone while
    # preserving its existing identifiers.
    device = phone
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

    phone_token_created = _demo_timestamp(days_ago=14, hours_ago=2)
    token = EnrollmentToken(
        verifier=b"d" * 32,
        pepper_version=1,
        bound_device_id=device.id,
        policy_revision_id=class_revision.id,
        status="consumed",
        expires_at=phone_token_created + timedelta(minutes=10),
        consumed_at=phone_token_created + timedelta(minutes=4),
        consumed_by_device_id=device.id,
        issued_by=str(administrator.administrator_uuid),
        reason=REASON,
        created_at=phone_token_created,
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
        issued_at=phone_token_created + timedelta(minutes=4),
        last_used_at=_demo_timestamp(hours_ago=2),
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
                created_at=phone_token_created - timedelta(minutes=5),
            ),
            DeviceEnrollmentEvent(
                device_id=device.id,
                credential_id=credential.id,
                token_id=token.id,
                category="token_issued",
                administrator_subject=str(administrator.administrator_uuid),
                reason=REASON,
                created_at=phone_token_created,
            ),
            DeviceEnrollmentEvent(
                device_id=device.id,
                credential_id=credential.id,
                token_id=token.id,
                category="token_consumed",
                reason="Enrollment token consumed by the enrolled phone",
                public_key_fingerprint=credential.public_key_fingerprint,
                created_at=phone_token_created + timedelta(minutes=4),
            ),
            DeviceEnrollmentEvent(
                device_id=device.id,
                credential_id=credential.id,
                token_id=token.id,
                category="enrollment_succeeded",
                reason="Device-owner enrollment completed",
                public_key_fingerprint=credential.public_key_fingerprint,
                created_at=phone_token_created + timedelta(minutes=5),
            ),
            DeviceLocationAssignment(
                device_id=device.id,
                target_type="class",
                target_name="Senior Five",
                responsible_officer="ICT Master",
                assigned_at=_demo_timestamp(days_ago=13).date(),
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
        assigned_at=_demo_timestamp(days_ago=12),
        superseded_at=_demo_timestamp(days_ago=1, hours_ago=2),
    )
    active_assignment = DevicePolicyAssignment(
        device_id=device.id,
        policy_revision_id=exam_revision.id,
        assigned_by_administrator_id=administrator.id,
        reason="Exam Mode Policy assigned for Senior Five examinations",
        status="active",
        assigned_at=_demo_timestamp(hours_ago=2),
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
                updated_at=_demo_timestamp(hours_ago=1),
            ),
        ]
    )

    check_in = DeviceCheckIn(
        check_in_uuid=uuid4(),
        device_id=device.id,
        credential_id=credential.id,
        observed_at=_demo_timestamp(hours_ago=1),
        elapsed_realtime_ms=86400000,
        boot_count=3,
        dpc_version=3,
        android_version="14",
        api_level=34,
        security_patch=_demo_timestamp(days_ago=1).date(),
        capabilities=["screen_time", "web_filter", "network_controls"],
        current_policy_uuid=EXAM_POLICY_UUID,
        current_revision_uuid=exam_revision.revision_uuid,
        policy_status="applied",
        enforcement_healthy=True,
        queued_event_count=0,
        content_hash=b"k" * 32,
        received_at=_demo_timestamp(minutes_ago=42),
    )
    db.session.add(check_in)
    db.session.flush()
    db.session.add_all(
        [
            DeviceComplianceState(
                device_id=device.id,
                last_check_in_id=check_in.id,
                last_observed_at=check_in.observed_at,
                last_received_at=check_in.received_at,
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
        observed_at=_demo_timestamp(hours_ago=3),
        elapsed_realtime_ms=86000000,
        boot_count=3,
        policy_uuid=CLASS_POLICY_UUID,
        revision_uuid=class_revision.revision_uuid,
        outcome="applied",
        content_hash=class_revision.content_hash,
        received_at=_demo_timestamp(hours_ago=2, minutes_ago=40),
    )
    exam_application = PolicyApplicationEvent(
        acknowledgement_uuid=uuid4(),
        device_id=device.id,
        credential_id=credential.id,
        observed_at=_demo_timestamp(hours_ago=2),
        elapsed_realtime_ms=86400000,
        boot_count=3,
        policy_uuid=EXAM_POLICY_UUID,
        revision_uuid=exam_revision.revision_uuid,
        outcome="applied",
        content_hash=exam_revision.content_hash,
        received_at=_demo_timestamp(hours_ago=1, minutes_ago=35),
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
            received_at=_demo_timestamp(minutes_ago=58),
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
        (
            "web_filter_blocked",
            "betting_domains",
            {"domain_hash": _domain_hash("1xbet.com")},
        ),
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
        (
            "policy_block",
            "blocked_social_app",
            {"package_name": "com.instagram.android", "message": "Instagram blocked"},
        ),
        (
            "web_filter_blocked",
            "betting_domains",
            {
                "domain_hash": _domain_hash("betway.com"),
                "message": "Betway request blocked",
            },
        ),
        (
            "tamper_attempt",
            "exam_kiosk_exit",
            {"attempt": "leave_exam_app", "message": "Kiosk exit attempt blocked"},
        ),
        (
            "configuration_changed",
            "block_mobile_network_changes",
            {"setting": "mobile_network", "message": "Mobile network change blocked"},
        ),
        (
            "policy_block",
            "blocked_game",
            {"package_name": "com.tencent.ig", "message": "PUBG Mobile blocked"},
        ),
        (
            "web_filter_blocked",
            "betting_domains",
            {
                "domain_hash": _domain_hash("bet365.com"),
                "message": "Bet365 request blocked",
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
                occurred_at=_demo_timestamp(days_ago=10 + sequence, hours_ago=3),
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
                received_at=_demo_timestamp(days_ago=10 + sequence, hours_ago=3),
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
        signature=key.sign(b"phone-audit-batch", ECDSA(hashes.SHA256())),
        content_hash=b"b" * 32,
        received_at=_demo_timestamp(minutes_ago=35),
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
            updated_at=_demo_timestamp(minutes_ago=24),
        )
    )
    db.session.add_all(
        [
            Incident(
                incident_number="NDEJJE-INC-001",
                device_id=device.id,
                incident_type="unauthorised_application",
                description="Blocked social application launch recorded during Class Time Policy.",
                reported_by="EDUGD DPC",
                status="OPEN",
                responsible_person="ICT Master",
                created_by_administrator_id=administrator.id,
                reported_at=_demo_timestamp(days_ago=8, hours_ago=2),
                created_at=_demo_timestamp(days_ago=8, hours_ago=3),
                updated_at=_demo_timestamp(days_ago=2),
            ),
            Incident(
                incident_number="NDEJJE-INC-002",
                device_id=device.id,
                incident_type="kiosk_bypass_attempt",
                description="Exam Mode kiosk exit attempt requires review.",
                reported_by="EDUGD DPC",
                status="OPEN",
                responsible_person="ICT Master",
                created_by_administrator_id=administrator.id,
                reported_at=_demo_timestamp(days_ago=5, hours_ago=2),
                created_at=_demo_timestamp(days_ago=5, hours_ago=3),
                updated_at=_demo_timestamp(days_ago=1, hours_ago=2),
            ),
        ]
    )
    phone_override = DeviceBlockOverride(
        device_id=phone.id,
        version=2,
        status="cleared",
        reason="Temporary examination hold cleared after review",
        issued_by_administrator_id=administrator.id,
        issued_at=_demo_timestamp(days_ago=1, hours_ago=4),
        cleared_by_administrator_id=administrator.id,
        cleared_at=_demo_timestamp(days_ago=1, hours_ago=3),
    )
    tablet_override = DeviceBlockOverride(
        device_id=tablet.id,
        version=1,
        status="active",
        reason="Tablet retained under an active safeguarding hold",
        issued_by_administrator_id=administrator.id,
        issued_at=_demo_timestamp(days_ago=2),
    )
    db.session.add_all([phone_override, tablet_override])
    db.session.flush()
    db.session.add_all(
        [
            DeviceControlEvent(
                device_id=phone.id,
                override_id=phone_override.id,
                administrator_id=administrator.id,
                operation="block",
                reason="Temporary examination hold applied",
                content_hash=hashlib.sha256(b"phone-block").digest(),
                created_at=_demo_timestamp(days_ago=1, hours_ago=4),
            ),
            DeviceControlEvent(
                device_id=phone.id,
                override_id=phone_override.id,
                administrator_id=administrator.id,
                operation="clear",
                reason="Temporary examination hold cleared after review",
                content_hash=hashlib.sha256(b"phone-clear").digest(),
                created_at=_demo_timestamp(days_ago=1, hours_ago=3),
            ),
            DeviceControlEvent(
                device_id=tablet.id,
                override_id=tablet_override.id,
                administrator_id=administrator.id,
                operation="block",
                reason="Tablet retained under an active safeguarding hold",
                content_hash=hashlib.sha256(b"tablet-block").digest(),
                created_at=_demo_timestamp(days_ago=2),
            ),
        ]
    )
    for day, minutes in enumerate(
        (96, 88, 104, 76, 91, 64, 112, 83, 77, 108, 69), start=0
    ):
        db.session.add(
            DeviceUsageDaily(
                device_id=phone.id,
                usage_date=_demo_timestamp(days_ago=day).date(),
                active_minutes=minutes,
                policy_uuid=EXAM_POLICY_UUID,
                revision_uuid=exam_revision.revision_uuid,
                reported_at=_demo_timestamp(days_ago=day, hours_ago=2),
            )
        )
    db.session.add(
        DeviceWebFilterEvent(
            device_id=phone.id,
            domain_hash=hashlib.sha256(b"bet365.com").digest(),
            rule_id="restricted-betting-domains",
            policy_uuid=EXAM_POLICY_UUID,
            revision_uuid=exam_revision.revision_uuid,
            observed_at=_demo_timestamp(days_ago=1, hours_ago=2),
            received_at=_demo_timestamp(days_ago=1, hours_ago=2),
        )
    )
    phone_pseudonym = hashlib.sha256(str(phone.device_uuid).encode()).digest()
    previous_sync: bytes | None = None
    for index, operation in enumerate(
        (
            "apply",
            "no_change",
            "rollback",
            "apply",
            "no_change",
            "apply",
            "no_change",
            "apply",
            "no_change",
            "apply",
            "no_change",
        ),
        start=1,
    ):
        event_hash = _hash_payload(
            {
                "device": str(phone.device_uuid),
                "sequence": index,
                "operation": operation,
                "previous": previous_sync.hex() if previous_sync else None,
            }
        )
        db.session.add(
            PolicySynchronizationEvent(
                device_id=phone.id,
                credential_id=credential.id,
                requested_device_pseudonym=phone_pseudonym,
                reported_client_version=index - 1,
                reported_policy_uuid=EXAM_POLICY_UUID,
                reported_revision_uuid=exam_revision.revision_uuid,
                server_policy_version=exam_revision.version,
                operation=operation,
                outcome_category="success",
                requested_at=_demo_timestamp(days_ago=index - 1, hours_ago=1),
                previous_event_hash=previous_sync,
                event_hash=event_hash,
            )
        )
        previous_sync = event_hash
    db.session.add(
        PolicySynchronizationChainHead(
            requested_device_pseudonym=phone_pseudonym,
            head_event_hash=previous_sync,
            updated_at=_demo_timestamp(minutes_ago=17),
        )
    )
    db.session.add_all(
        [
            DeviceAssetChangeEvent(
                device_id=phone.id,
                administrator_id=administrator.id,
                operation="corrected",
                changed_fields=["condition", "asset_notes"],
                reason="Verified asset inspection after issue review",
                created_at=_demo_timestamp(days_ago=4),
            ),
            DeviceAssetChangeEvent(
                device_id=tablet.id,
                administrator_id=administrator.id,
                operation="corrected",
                changed_fields=["department", "asset_lifecycle_status"],
                reason="Assigned tablet to the Computer Studies department",
                created_at=_demo_timestamp(days_ago=7),
            ),
            AdministratorAuthenticationEvent(
                administrator_id=administrator.id,
                category="login_succeeded",
                reason="Administrator sign-in",
                created_at=_demo_timestamp(days_ago=20),
            ),
            AdministratorAuthenticationEvent(
                administrator_id=administrator.id,
                category="logout",
                reason="Administrator sign-out",
                created_at=_demo_timestamp(days_ago=19, hours_ago=1),
            ),
            *[
                AdministratorAuthenticationEvent(
                    administrator_id=administrator.id,
                    category="login_succeeded",
                    reason="Daily administrator operations review",
                    created_at=_demo_timestamp(days_ago=day, hours_ago=4),
                )
                for day in range(0, 10)
            ],
        ]
    )
    active_token = EnrollmentToken(
        verifier=b"a" * 32,
        pepper_version=1,
        policy_revision_id=class_revision.id,
        status="active",
        expires_at=now + timedelta(minutes=10),
        issued_by=str(administrator.administrator_uuid),
        reason="Provisioning token ready for the next approved school-owned device",
        created_at=_demo_timestamp(hours_ago=1),
    )
    revoked_token = EnrollmentToken(
        verifier=b"r" * 32,
        pepper_version=1,
        policy_revision_id=exam_revision.id,
        status="revoked",
        expires_at=_demo_timestamp(days_ago=2, hours_ago=1),
        issued_by=str(administrator.administrator_uuid),
        reason="Superseded provisioning request",
        created_at=_demo_timestamp(days_ago=3),
        revoked_at=_demo_timestamp(days_ago=2, hours_ago=20),
        revoked_by=str(administrator.administrator_uuid),
        revocation_reason="Superseded provisioning request",
    )
    db.session.add_all([active_token, revoked_token])
    _seed_tablet_operations(
        tablet=tablet,
        administrator=administrator,
        policy=class_policy,
        revision=class_revision,
    )
    db.session.commit()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed the disposable NDEJJE SS operational scenario"
    )
    parser.add_argument(
        "--blank-school",
        action="store_true",
        help="leave the school profile empty so it can be created in the dashboard",
    )
    args = parser.parse_args()
    application = create_app("development")
    with application.app_context():
        _seed(blank_school=args.blank_school)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
