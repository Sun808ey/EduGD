import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import SupportsIndex
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.device_identity import ANDROID_VERSION_BY_API_LEVEL
from app.extensions import db

ANDROID_PACKAGE_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
)
DEVICE_STATUSES = frozenset({"active", "suspended", "retired"})
POLICY_STATUSES = frozenset({"draft", "active", "inactive", "revoked"})
DEVICE_REGISTRATION_EVENT_TYPES = frozenset(
    {
        "registered",
        "duplicate",
        "upgrade_requires_authentication",
        "downgrade_rejected",
    }
)
ENROLLMENT_TOKEN_STATUSES = frozenset(
    {"active", "consumed", "revoked", "expired", "locked"}
)
DEVICE_CREDENTIAL_STATUSES = frozenset({"active", "revoked", "superseded"})
DEVICE_CREDENTIAL_ALGORITHMS = frozenset({"RSA_2048_SHA256"})
DEVICE_ENROLLMENT_EVENT_CATEGORIES = frozenset(
    {
        "token_issued",
        "token_revoked",
        "token_consumed",
        "enrollment_succeeded",
        "enrollment_failed",
        "credential_rotated",
        "credential_revoked",
        "authentication_failed",
        "authentication_succeeded",
        "legacy_authentication_used",
        "legacy_authentication_disabled",
    }
)
DEVICE_ENROLLMENT_STATES = frozenset({"legacy_pending", "enrolled"})
ADMINISTRATOR_STATUSES = frozenset({"active", "disabled", "locked"})
ADMINISTRATOR_PERMISSIONS = frozenset(
    {
        "administrator.manage",
        "enrollment_token.issue",
        "enrollment_token.revoke",
        "device_credential.revoke",
    }
)
ADMINISTRATOR_AUTHENTICATION_EVENT_CATEGORIES = frozenset(
    {
        "bootstrap",
        "login_succeeded",
        "login_failed",
        "account_locked",
        "account_unlocked",
        "password_reset",
        "logout",
        "session_revoked",
        "account_disabled",
        "permission_granted",
        "permission_revoked",
        "authorization_failed",
    }
)
ADMINISTRATOR_USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,64}$")
ADMINISTRATOR_FAILURE_CLASS_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_printable_text(value: object, field: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or not value.isprintable()
    ):
        raise ValueError(f"{field} must contain 1 to {maximum} printable characters")
    return value


def _validate_blocked_apps(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(
            "blocked_apps must contain valid Android package identifiers"
        )
    is_valid = all(
        isinstance(package_name, str)
        and ANDROID_PACKAGE_PATTERN.fullmatch(package_name) is not None
        for package_name in value
    )
    if not is_valid or len(value) != len(set(value)):
        raise ValueError(
            "blocked_apps must contain valid Android package identifiers"
        )
    return list(value)


class BlockedAppList(MutableList[str]):
    """Atomically validate every in-place blocked-app list mutation."""

    @classmethod
    def coerce(cls, key: str, value: object) -> "BlockedAppList":
        if isinstance(value, cls):
            return value
        return cls(_validate_blocked_apps(value))

    def _replace(self, candidate: list[str]) -> None:
        validated = _validate_blocked_apps(candidate)
        list.clear(self)
        list.extend(self, validated)
        self.changed()

    def append(self, value: str) -> None:
        self._replace([*self, value])

    def extend(self, values: Iterable[str]) -> None:
        self._replace([*self, *values])

    def insert(self, index: SupportsIndex, value: str) -> None:
        candidate = list(self)
        candidate.insert(index, value)
        self._replace(candidate)

    def __setitem__(
        self,
        index: SupportsIndex | slice,
        value: str | Iterable[str],
    ) -> None:
        candidate = list(self)
        if isinstance(index, slice):
            candidate[index] = value
        else:
            if not isinstance(value, str):
                raise ValueError(
                    "blocked_apps must contain valid Android package identifiers"
                )
            candidate[index] = value
        self._replace(candidate)

    def __imul__(self, value: SupportsIndex) -> "BlockedAppList":
        candidate = list(self)
        candidate *= value
        self._replace(candidate)
        return self


class Administrator(db.Model):
    __tablename__ = "administrators"
    __table_args__ = (
        UniqueConstraint(
            "administrator_uuid",
            name="uq_administrators_uuid",
        ),
        UniqueConstraint("username", name="uq_administrators_username"),
        CheckConstraint(
            "status IN ('active', 'disabled', 'locked')",
            name="ck_administrators_status",
        ),
        CheckConstraint(
            "length(username) BETWEEN 3 AND 64 AND username = lower(username)",
            name="ck_administrators_username_bounded",
        ),
        CheckConstraint(
            "length(display_name) BETWEEN 1 AND 120",
            name="ck_administrators_display_name_bounded",
        ),
        CheckConstraint(
            "length(password_verifier) BETWEEN 1 AND 512 AND "
            "password_verifier LIKE 'scrypt:%'",
            name="ck_administrators_password_verifier",
        ),
        CheckConstraint(
            "failed_attempts BETWEEN 0 AND 5",
            name="ck_administrators_failed_attempts",
        ),
        CheckConstraint(
            "(status = 'active' AND failed_attempts BETWEEN 0 AND 4 AND "
            "lock_expires_at IS NULL AND disabled_at IS NULL) OR "
            "(status = 'locked' AND failed_attempts = 5 AND "
            "lock_expires_at IS NOT NULL AND lock_expires_at > updated_at AND "
            "disabled_at IS NULL) OR "
            "(status = 'disabled' AND lock_expires_at IS NULL AND "
            "disabled_at IS NOT NULL)",
            name="ck_administrators_lifecycle",
        ),
        Index("ix_administrators_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    administrator_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_verifier: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    lock_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    permissions: Mapped[list["AdministratorPermission"]] = relationship(
        back_populates="administrator",
        foreign_keys="AdministratorPermission.administrator_id",
        order_by="AdministratorPermission.granted_at",
    )
    sessions: Mapped[list["AdministratorSession"]] = relationship(
        back_populates="administrator",
        foreign_keys="AdministratorSession.administrator_id",
        order_by="AdministratorSession.issued_at",
    )
    authentication_events: Mapped[list["AdministratorAuthenticationEvent"]] = (
        relationship(
            back_populates="administrator",
            foreign_keys="AdministratorAuthenticationEvent.administrator_id",
            order_by="AdministratorAuthenticationEvent.created_at",
        )
    )

    @validates("username")
    def validate_username(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or not ADMINISTRATOR_USERNAME_PATTERN.fullmatch(
            value
        ):
            raise ValueError("invalid administrator username")
        return value

    @validates("display_name")
    def validate_display_name(self, _key: str, value: object) -> str:
        return _validate_printable_text(value, "administrator display name", 120)

    @validates("password_verifier")
    def validate_password_verifier(self, _key: str, value: object) -> str:
        if (
            not isinstance(value, str)
            or not 1 <= len(value) <= 512
            or not value.startswith("scrypt:")
        ):
            raise ValueError("invalid administrator password verifier")
        return value

    @validates("status")
    def validate_status(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in ADMINISTRATOR_STATUSES:
            raise ValueError("invalid administrator status")
        return value

    @validates("failed_attempts")
    def validate_failed_attempts(self, _key: str, value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
            raise ValueError("administrator failed attempts must be between 0 and 5")
        return value


class AdministratorPermission(db.Model):
    __tablename__ = "administrator_permissions"
    __table_args__ = (
        UniqueConstraint(
            "administrator_id",
            "permission",
            name="uq_administrator_permissions_administrator_permission",
        ),
        CheckConstraint(
            "permission IN ('administrator.manage', "
            "'enrollment_token.issue', 'enrollment_token.revoke', "
            "'device_credential.revoke')",
            name="ck_administrator_permissions_permission",
        ),
        CheckConstraint(
            "(granted_by_administrator_id IS NOT NULL AND "
            "trusted_operator_subject IS NULL) OR "
            "(granted_by_administrator_id IS NULL AND "
            "trusted_operator_subject IS NOT NULL)",
            name="ck_administrator_permissions_grant_actor",
        ),
        CheckConstraint(
            "length(reason) BETWEEN 1 AND 512",
            name="ck_administrator_permissions_reason_bounded",
        ),
        CheckConstraint(
            "trusted_operator_subject IS NULL OR "
            "length(trusted_operator_subject) BETWEEN 1 AND 255",
            name="ck_administrator_permissions_operator_bounded",
        ),
        Index("ix_administrator_permissions_administrator", "administrator_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    administrator_id: Mapped[int] = mapped_column(
        ForeignKey("administrators.id", ondelete="RESTRICT"),
        nullable=False,
    )
    permission: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_by_administrator_id: Mapped[int | None] = mapped_column(
        ForeignKey("administrators.id", ondelete="RESTRICT"),
        nullable=True,
    )
    trusted_operator_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    administrator: Mapped[Administrator] = relationship(
        back_populates="permissions",
        foreign_keys=[administrator_id],
    )
    granted_by_administrator: Mapped[Administrator | None] = relationship(
        foreign_keys=[granted_by_administrator_id],
    )

    @validates("permission")
    def validate_permission(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in ADMINISTRATOR_PERMISSIONS:
            raise ValueError("invalid administrator permission")
        return value

    @validates("trusted_operator_subject")
    def validate_trusted_operator_subject(
        self,
        _key: str,
        value: object,
    ) -> str | None:
        if value is None:
            return None
        return _validate_printable_text(value, "trusted operator subject", 255)

    @validates("reason")
    def validate_reason(self, _key: str, value: object) -> str:
        return _validate_printable_text(value, "permission grant reason", 512)


class AdministratorSession(db.Model):
    __tablename__ = "administrator_sessions"
    __table_args__ = (
        UniqueConstraint("jti_digest", name="uq_administrator_sessions_jti_digest"),
        CheckConstraint(
            "expires_at > issued_at",
            name="ck_administrator_sessions_expiry",
        ),
        CheckConstraint(
            "length(jti_digest) = 32",
            name="ck_administrator_sessions_jti_digest_length",
        ),
        CheckConstraint(
            "source_address_pseudonym IS NULL OR length(source_address_pseudonym) = 32",
            name="ck_administrator_sessions_source_pseudonym_length",
        ),
        CheckConstraint(
            "(revoked_at IS NULL AND revoked_by_administrator_id IS NULL AND "
            "revoked_by_operator_subject IS NULL AND revocation_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_at >= issued_at AND "
            "revocation_reason IS NOT NULL AND "
            "((revoked_by_administrator_id IS NOT NULL AND "
            "revoked_by_operator_subject IS NULL) OR "
            "(revoked_by_administrator_id IS NULL AND "
            "revoked_by_operator_subject IS NOT NULL)))",
            name="ck_administrator_sessions_revocation_state",
        ),
        CheckConstraint(
            "(revoked_by_operator_subject IS NULL OR "
            "length(revoked_by_operator_subject) BETWEEN 1 AND 255) AND "
            "(revocation_reason IS NULL OR "
            "length(revocation_reason) BETWEEN 1 AND 512)",
            name="ck_administrator_sessions_revocation_metadata_bounded",
        ),
        Index(
            "ix_administrator_sessions_administrator_expires",
            "administrator_id",
            "expires_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    administrator_id: Mapped[int] = mapped_column(
        ForeignKey("administrators.id", ondelete="RESTRICT"),
        nullable=False,
    )
    jti_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    source_address_pseudonym: Mapped[bytes | None] = mapped_column(
        LargeBinary(32),
        nullable=True,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_by_administrator_id: Mapped[int | None] = mapped_column(
        ForeignKey("administrators.id", ondelete="RESTRICT"),
        nullable=True,
    )
    revoked_by_operator_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    revocation_reason: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    administrator: Mapped[Administrator] = relationship(
        back_populates="sessions",
        foreign_keys=[administrator_id],
    )
    revoked_by_administrator: Mapped[Administrator | None] = relationship(
        foreign_keys=[revoked_by_administrator_id],
    )

    @validates("jti_digest")
    def validate_jti_digest(self, _key: str, value: object) -> bytes:
        if not isinstance(value, bytes) or len(value) != 32:
            raise ValueError("administrator session JTI digest must contain 32 bytes")
        return value

    @validates("source_address_pseudonym")
    def validate_source_address_pseudonym(
        self,
        _key: str,
        value: object,
    ) -> bytes | None:
        if value is not None and (not isinstance(value, bytes) or len(value) != 32):
            raise ValueError("source address pseudonym must contain 32 bytes")
        return value

    @validates("revoked_by_operator_subject")
    def validate_revoked_by_operator_subject(
        self,
        _key: str,
        value: object,
    ) -> str | None:
        if value is None:
            return None
        return _validate_printable_text(value, "revoking operator subject", 255)

    @validates("revocation_reason")
    def validate_revocation_reason(
        self,
        _key: str,
        value: object,
    ) -> str | None:
        if value is None:
            return None
        return _validate_printable_text(value, "session revocation reason", 512)


class AdministratorAuthenticationEvent(db.Model):
    __tablename__ = "administrator_authentication_events"
    __table_args__ = (
        UniqueConstraint(
            "event_uuid",
            name="uq_administrator_authentication_events_uuid",
        ),
        CheckConstraint(
            "category IN ('bootstrap', 'login_succeeded', 'login_failed', "
            "'account_locked', 'account_unlocked', 'password_reset', 'logout', "
            "'session_revoked', 'account_disabled', 'permission_granted', "
            "'permission_revoked', 'authorization_failed')",
            name="ck_administrator_authentication_events_category",
        ),
        CheckConstraint(
            "acting_administrator_id IS NULL OR trusted_operator_subject IS NULL",
            name="ck_administrator_authentication_events_actor",
        ),
        CheckConstraint(
            "failure_class IS NULL OR length(failure_class) BETWEEN 1 AND 64",
            name="ck_administrator_authentication_events_failure_bounded",
        ),
        CheckConstraint(
            "source_address_pseudonym IS NULL OR length(source_address_pseudonym) = 32",
            name="ck_administrator_authentication_events_source_pseudonym_length",
        ),
        CheckConstraint(
            "(trusted_operator_subject IS NULL OR "
            "length(trusted_operator_subject) BETWEEN 1 AND 255) AND "
            "(reason IS NULL OR length(reason) BETWEEN 1 AND 512)",
            name="ck_administrator_authentication_events_metadata_bounded",
        ),
        Index(
            "ix_administrator_authentication_events_administrator_created",
            "administrator_id",
            "created_at",
        ),
        Index(
            "ix_administrator_authentication_events_category_created",
            "category",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    administrator_id: Mapped[int | None] = mapped_column(
        ForeignKey("administrators.id", ondelete="RESTRICT"),
        nullable=True,
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("administrator_sessions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_address_pseudonym: Mapped[bytes | None] = mapped_column(
        LargeBinary(32),
        nullable=True,
    )
    acting_administrator_id: Mapped[int | None] = mapped_column(
        ForeignKey("administrators.id", ondelete="RESTRICT"),
        nullable=True,
    )
    trusted_operator_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    administrator: Mapped[Administrator | None] = relationship(
        back_populates="authentication_events",
        foreign_keys=[administrator_id],
    )
    session: Mapped[AdministratorSession | None] = relationship(
        foreign_keys=[session_id],
    )
    acting_administrator: Mapped[Administrator | None] = relationship(
        foreign_keys=[acting_administrator_id],
    )

    @validates("category")
    def validate_category(self, _key: str, value: object) -> str:
        if (
            not isinstance(value, str)
            or value not in ADMINISTRATOR_AUTHENTICATION_EVENT_CATEGORIES
        ):
            raise ValueError("invalid administrator authentication event category")
        return value

    @validates("failure_class")
    def validate_failure_class(
        self,
        _key: str,
        value: object,
    ) -> str | None:
        if value is not None and (
            not isinstance(value, str)
            or not ADMINISTRATOR_FAILURE_CLASS_PATTERN.fullmatch(value)
        ):
            raise ValueError("invalid administrator authentication failure class")
        return value

    @validates("source_address_pseudonym")
    def validate_source_address_pseudonym(
        self,
        _key: str,
        value: object,
    ) -> bytes | None:
        if value is not None and (not isinstance(value, bytes) or len(value) != 32):
            raise ValueError("source address pseudonym must contain 32 bytes")
        return value

    @validates("trusted_operator_subject")
    def validate_trusted_operator_subject(
        self,
        _key: str,
        value: object,
    ) -> str | None:
        if value is None:
            return None
        return _validate_printable_text(value, "trusted operator subject", 255)

    @validates("reason")
    def validate_reason(self, _key: str, value: object) -> str | None:
        if value is None:
            return None
        return _validate_printable_text(value, "authentication event reason", 512)


class Device(db.Model):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("device_uuid", name="uq_devices_device_uuid"),
        Index("ix_devices_device_uuid", "device_uuid"),
        CheckConstraint(
            "status IN ('active', 'suspended', 'retired')",
            name="ck_devices_status",
        ),
        CheckConstraint(
            "api_level BETWEEN 21 AND 29",
            name="ck_devices_api_level_supported",
        ),
        CheckConstraint(
            "(android_version = '5.0' AND api_level = 21) OR "
            "(android_version = '5.1' AND api_level = 22) OR "
            "(android_version = '6.0' AND api_level = 23) OR "
            "(android_version = '7.0' AND api_level = 24) OR "
            "(android_version = '7.1' AND api_level = 25) OR "
            "(android_version = '8.0' AND api_level = 26) OR "
            "(android_version = '8.1' AND api_level = 27) OR "
            "(android_version = '9' AND api_level = 28) OR "
            "(android_version = '10' AND api_level = 29)",
            name="ck_devices_android_api_match",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    android_version: Mapped[str] = mapped_column(String(32), nullable=False)
    api_level: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    legacy_enrollment_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    policy_assignments: Mapped[list["DevicePolicyAssignment"]] = relationship(
        back_populates="device",
        order_by="DevicePolicyAssignment.assigned_at",
    )
    registration_events: Mapped[list["DeviceRegistrationEvent"]] = relationship(
        back_populates="device",
        order_by="DeviceRegistrationEvent.created_at",
    )
    credentials: Mapped[list["DeviceCredential"]] = relationship(
        back_populates="device",
        foreign_keys="DeviceCredential.device_id",
        order_by="DeviceCredential.issued_at",
    )

    @property
    def enrollment_state(self) -> str:
        if any(credential.status == "active" for credential in self.credentials):
            return "enrolled"
        return "legacy_pending"

    @validates("status")
    def validate_status(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in DEVICE_STATUSES:
            raise ValueError("invalid device status")
        return value

    @validates("android_version")
    def validate_android_version(self, _key: str, value: object) -> str:
        if (
            not isinstance(value, str)
            or value not in ANDROID_VERSION_BY_API_LEVEL.values()
        ):
            raise ValueError("unsupported Android version")
        return value

    @validates("api_level")
    def validate_api_level(self, _key: str, value: object) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value not in ANDROID_VERSION_BY_API_LEVEL
        ):
            raise ValueError("unsupported Android API level")
        return value


class Policy(db.Model):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("policy_uuid", name="uq_policies_policy_uuid"),
        Index("ix_policies_policy_uuid", "policy_uuid"),
        CheckConstraint("version >= 1", name="ck_policies_version_positive"),
        CheckConstraint(
            "status IN ('draft', 'active', 'inactive', 'revoked')",
            name="ck_policies_status",
        ),
        CheckConstraint(
            "edug_valid_blocked_apps(blocked_apps)",
            name="ck_policies_blocked_apps",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    blocked_apps: Mapped[list[str]] = mapped_column(
        BlockedAppList.as_mutable(JSON),
        nullable=False,
        default=list,
        server_default="[]",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    device_assignments: Mapped[list["DevicePolicyAssignment"]] = relationship(
        back_populates="policy",
        order_by="DevicePolicyAssignment.assigned_at",
    )

    @validates("blocked_apps")
    def validate_blocked_apps(
        self,
        _key: str,
        value: object,
    ) -> list[str]:
        return _validate_blocked_apps(value)

    @validates("status")
    def validate_status(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in POLICY_STATUSES:
            raise ValueError("invalid policy status")
        return value


class DeviceRegistrationEvent(db.Model):
    __tablename__ = "device_registration_events"
    __table_args__ = (
        UniqueConstraint("event_uuid", name="uq_device_registration_events_uuid"),
        CheckConstraint(
            "event_type IN ('registered', 'duplicate', "
            "'upgrade_requires_authentication', 'downgrade_rejected')",
            name="ck_device_registration_events_type",
        ),
        CheckConstraint(
            "reported_api_level BETWEEN 21 AND 29",
            name="ck_device_registration_events_reported_api_level",
        ),
        CheckConstraint(
            "stored_api_level BETWEEN 21 AND 29",
            name="ck_device_registration_events_stored_api_level",
        ),
        Index(
            "ix_device_registration_events_device_created",
            "device_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stored_android_version: Mapped[str] = mapped_column(String(32), nullable=False)
    stored_api_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reported_android_version: Mapped[str] = mapped_column(String(32), nullable=False)
    reported_api_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    device: Mapped[Device] = relationship(back_populates="registration_events")

    @validates("event_type")
    def validate_event_type(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in DEVICE_REGISTRATION_EVENT_TYPES:
            raise ValueError("invalid device registration event type")
        return value


class EnrollmentToken(db.Model):
    __tablename__ = "enrollment_tokens"
    __table_args__ = (
        UniqueConstraint("token_uuid", name="uq_enrollment_tokens_uuid"),
        CheckConstraint(
            "status IN ('active', 'consumed', 'revoked', 'expired', 'locked')",
            name="ck_enrollment_tokens_status",
        ),
        CheckConstraint(
            "failed_attempts BETWEEN 0 AND 5",
            name="ck_enrollment_tokens_failed_attempts",
        ),
        CheckConstraint(
            "pepper_version >= 1",
            name="ck_enrollment_tokens_pepper_version",
        ),
        CheckConstraint(
            "length(verifier) = 32",
            name="ck_enrollment_tokens_verifier_length",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_enrollment_tokens_expiry",
        ),
        CheckConstraint(
            "(status = 'consumed' AND consumed_at IS NOT NULL AND "
            "consumed_by_device_id IS NOT NULL) OR "
            "(status <> 'consumed' AND consumed_at IS NULL AND "
            "consumed_by_device_id IS NULL)",
            name="ck_enrollment_tokens_consumption_state",
        ),
        CheckConstraint(
            "(status = 'revoked' AND revoked_at IS NOT NULL AND "
            "revoked_by IS NOT NULL AND revocation_reason IS NOT NULL) OR "
            "(status <> 'revoked' AND revoked_at IS NULL AND "
            "revoked_by IS NULL AND revocation_reason IS NULL)",
            name="ck_enrollment_tokens_revocation_state",
        ),
        Index("ix_enrollment_tokens_status_expires", "status", "expires_at"),
        Index("ix_enrollment_tokens_bound_device", "bound_device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    verifier: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    pepper_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    bound_device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    consumed_by_device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=True,
    )
    issued_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    @validates("status")
    def validate_status(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in ENROLLMENT_TOKEN_STATUSES:
            raise ValueError("invalid enrollment token status")
        return value

    @validates("verifier")
    def validate_verifier(self, _key: str, value: object) -> bytes:
        if not isinstance(value, bytes) or len(value) != 32:
            raise ValueError("enrollment token verifier must contain 32 bytes")
        return value


class DeviceCredential(db.Model):
    __tablename__ = "device_credentials"
    __table_args__ = (
        UniqueConstraint("credential_uuid", name="uq_device_credentials_uuid"),
        UniqueConstraint(
            "public_key_fingerprint",
            name="uq_device_credentials_public_key_fingerprint",
        ),
        CheckConstraint(
            "algorithm IN ('RSA_2048_SHA256')",
            name="ck_device_credentials_algorithm",
        ),
        CheckConstraint(
            "status IN ('active', 'revoked', 'superseded')",
            name="ck_device_credentials_status",
        ),
        CheckConstraint(
            "length(public_key_der) BETWEEN 1 AND 512",
            name="ck_device_credentials_public_key_length",
        ),
        CheckConstraint(
            "length(public_key_fingerprint) = 32",
            name="ck_device_credentials_fingerprint_length",
        ),
        CheckConstraint(
            "(status = 'active' AND revoked_at IS NULL AND revoked_by IS NULL "
            "AND revocation_reason IS NULL AND superseded_at IS NULL AND "
            "superseded_by_id IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL AND "
            "revoked_by IS NOT NULL AND revocation_reason IS NOT NULL AND "
            "superseded_at IS NULL AND superseded_by_id IS NULL) OR "
            "(status = 'superseded' AND revoked_at IS NULL AND "
            "revoked_by IS NULL AND revocation_reason IS NULL AND "
            "superseded_at IS NOT NULL)",
            name="ck_device_credentials_lifecycle",
        ),
        Index(
            "uq_device_credentials_active_device",
            "device_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index("ix_device_credentials_device_status", "device_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credential_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    enrollment_token_id: Mapped[int | None] = mapped_column(
        ForeignKey("enrollment_tokens.id", ondelete="RESTRICT"),
        nullable=True,
    )
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    public_key_der: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    public_key_fingerprint: Mapped[bytes] = mapped_column(
        LargeBinary(32),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    superseded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("device_credentials.id", ondelete="RESTRICT"),
        nullable=True,
    )

    device: Mapped[Device] = relationship(
        back_populates="credentials",
        foreign_keys=[device_id],
    )

    @validates("algorithm")
    def validate_algorithm(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in DEVICE_CREDENTIAL_ALGORITHMS:
            raise ValueError("invalid device credential algorithm")
        return value

    @validates("status")
    def validate_status(self, _key: str, value: object) -> str:
        if not isinstance(value, str) or value not in DEVICE_CREDENTIAL_STATUSES:
            raise ValueError("invalid device credential status")
        return value

    @validates("public_key_fingerprint")
    def validate_public_key_fingerprint(self, _key: str, value: object) -> bytes:
        if not isinstance(value, bytes) or len(value) != 32:
            raise ValueError("public key fingerprint must contain 32 bytes")
        return value

    @validates("public_key_der")
    def validate_public_key_der(self, _key: str, value: object) -> bytes:
        if not isinstance(value, bytes) or not 1 <= len(value) <= 512:
            raise ValueError("public key DER must contain 1 to 512 bytes")
        return value


class DeviceRequestNonce(db.Model):
    __tablename__ = "device_request_nonces"
    __table_args__ = (
        UniqueConstraint(
            "credential_id",
            "nonce_hash",
            name="uq_device_request_nonces_credential_hash",
        ),
        CheckConstraint(
            "expires_at > observed_at",
            name="ck_device_request_nonces_expiry",
        ),
        CheckConstraint(
            "length(nonce_hash) = 32",
            name="ck_device_request_nonces_hash_length",
        ),
        Index("ix_device_request_nonces_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credential_id: Mapped[int] = mapped_column(
        ForeignKey("device_credentials.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nonce_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    @validates("nonce_hash")
    def validate_nonce_hash(self, _key: str, value: object) -> bytes:
        if not isinstance(value, bytes) or len(value) != 32:
            raise ValueError("device request nonce hash must contain 32 bytes")
        return value


class DeviceEnrollmentEvent(db.Model):
    __tablename__ = "device_enrollment_events"
    __table_args__ = (
        UniqueConstraint("event_uuid", name="uq_device_enrollment_events_uuid"),
        CheckConstraint(
            "category IN ('token_issued', 'token_revoked', "
            "'token_consumed', 'enrollment_succeeded', 'enrollment_failed', "
            "'credential_rotated', 'credential_revoked', "
            "'authentication_succeeded', 'authentication_failed', "
            "'legacy_authentication_used', "
            "'legacy_authentication_disabled')",
            name="ck_device_enrollment_events_category",
        ),
        CheckConstraint(
            "public_key_fingerprint IS NULL OR length(public_key_fingerprint) = 32",
            name="ck_device_enrollment_events_fingerprint_length",
        ),
        Index(
            "ix_device_enrollment_events_device_created",
            "device_id",
            "created_at",
        ),
        Index(
            "ix_device_enrollment_events_credential_created",
            "credential_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=True,
    )
    credential_id: Mapped[int | None] = mapped_column(
        ForeignKey("device_credentials.id", ondelete="RESTRICT"),
        nullable=True,
    )
    token_id: Mapped[int | None] = mapped_column(
        ForeignKey("enrollment_tokens.id", ondelete="RESTRICT"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    administrator_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    public_key_fingerprint: Mapped[bytes | None] = mapped_column(
        LargeBinary(32),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    @validates("category")
    def validate_category(self, _key: str, value: object) -> str:
        if (
            not isinstance(value, str)
            or value not in DEVICE_ENROLLMENT_EVENT_CATEGORIES
        ):
            raise ValueError("invalid device enrollment event category")
        return value

    @validates("public_key_fingerprint")
    def validate_public_key_fingerprint(
        self,
        _key: str,
        value: object,
    ) -> bytes | None:
        if value is not None and (not isinstance(value, bytes) or len(value) != 32):
            raise ValueError("public key fingerprint must contain 32 bytes")
        return value


class DevicePolicyAssignment(db.Model):
    __tablename__ = "device_policy_assignments"
    __table_args__ = (
        CheckConstraint(
            "policy_version >= 1",
            name="ck_device_policy_assignments_version_positive",
        ),
        CheckConstraint(
            "status IN ('active', 'superseded')",
            name="ck_device_policy_assignments_status",
        ),
        CheckConstraint(
            "(status = 'active' AND superseded_at IS NULL) OR "
            "(status = 'superseded' AND superseded_at IS NOT NULL)",
            name="ck_device_policy_assignments_status_timestamp",
        ),
        Index(
            "uq_device_policy_assignments_active_device",
            "device_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "ix_device_policy_assignments_device_history",
            "device_id",
            "assigned_at",
        ),
        Index("ix_device_policy_assignments_policy_id", "policy_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    device: Mapped[Device] = relationship(back_populates="policy_assignments")
    policy: Mapped[Policy] = relationship(back_populates="device_assignments")


__all__ = [
    "ADMINISTRATOR_AUTHENTICATION_EVENT_CATEGORIES",
    "ADMINISTRATOR_PERMISSIONS",
    "ADMINISTRATOR_STATUSES",
    "Administrator",
    "AdministratorAuthenticationEvent",
    "AdministratorPermission",
    "AdministratorSession",
    "DEVICE_CREDENTIAL_ALGORITHMS",
    "DEVICE_CREDENTIAL_STATUSES",
    "DEVICE_ENROLLMENT_EVENT_CATEGORIES",
    "DEVICE_ENROLLMENT_STATES",
    "DEVICE_REGISTRATION_EVENT_TYPES",
    "DEVICE_STATUSES",
    "ENROLLMENT_TOKEN_STATUSES",
    "Device",
    "DeviceCredential",
    "DeviceEnrollmentEvent",
    "DevicePolicyAssignment",
    "DeviceRegistrationEvent",
    "DeviceRequestNonce",
    "EnrollmentToken",
    "Policy",
    "POLICY_STATUSES",
]
