import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


def utc_now() -> datetime:
    return datetime.now(UTC)


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
        MutableList.as_mutable(JSON),
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


__all__ = ["DEVICE_STATUSES", "Device", "DevicePolicyAssignment", "Policy"]
