from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.models import PolicyAssignmentChainHead, PolicySynchronizationChainHead
from app.services.audit_verification import AuditChainVerificationError
from scripts.compare_database_inventories import compare
from scripts.database_inventory import canonical, encoded, verify_audit


def test_fingerprints_preserve_types_and_normalize_time() -> None:
    value = datetime(2026, 9, 9, tzinfo=UTC)
    assert encoded(value) == encoded(value.astimezone(timezone(timedelta(hours=3))))
    assert encoded({"b": 2, "a": 1}) == encoded({"a": 1, "b": 2})
    assert encoded(b"1") != encoded("1")
    assert encoded(Decimal("1.01")) != encoded(1.01)
    assert canonical(uuid4()).keys() == {"uuid"}
    assert encoded(memoryview(b"x")) == encoded(b"x")
    with pytest.raises(TypeError):
        encoded(object())


def frozen_report() -> dict:
    return {
        "format_version": 1,
        "tls_verified": True,
        "writers_stopped": True,
        "audit": {"revisions": 1},
        "missing_application_tables": [],
        "migration_heads": ["head"],
        "tables": {"devices": {"row_count": 1, "sha256": "a" * 64}},
        "sequences": [],
        "sequence_definitions": [],
        "triggers": [],
        "functions": [],
        "row_security": [],
    }


def test_comparison_detects_data_and_evidence_changes() -> None:
    assert compare(frozen_report(), frozen_report(), "head") == []
    for field in (
        "tables",
        "sequences",
        "triggers",
        "functions",
        "row_security",
        "audit",
    ):
        target = frozen_report()
        target[field] = None
        assert compare(frozen_report(), target, "head")


@pytest.mark.parametrize(
    "field",
    [
        "sequences",
        "sequence_definitions",
        "triggers",
        "functions",
        "row_security",
        "audit",
        "tables",
    ],
)
def test_matching_incomplete_reports_cannot_pass(field: str) -> None:
    report = frozen_report()
    del report[field]
    assert compare(report, report, "head")


def test_malformed_inventory_cannot_pass() -> None:
    assert compare([], [], "head")
    for value in (
        [],
        {"devices": None},
        {"devices": {"sha256": "fake", "row_count": 1}},
    ):
        report = frozen_report()
        report["tables"] = value
        assert compare(report, report, "head")


@pytest.mark.parametrize(
    "field,value",
    [
        ("tls_verified", False),
        ("writers_stopped", False),
        ("migration_heads", ["old"]),
        ("missing_application_tables", ["devices"]),
        ("format_version", 0),
    ],
)
def test_incomplete_inventory_never_passes(field: str, value: object) -> None:
    target = frozen_report()
    target[field] = value
    assert compare(frozen_report(), target, "head")


def test_audit_verification_does_not_write(app: Flask) -> None:
    with app.app_context():
        assert verify_audit() == {
            "revisions": 0,
            "assignment_chains": 0,
            "sync_chains": 0,
        }
        assert list(db.session.scalars(select(PolicyAssignmentChainHead))) == []


def test_orphan_sync_head_is_not_ignored(app: Flask) -> None:
    with app.app_context():
        db.session.add(
            PolicySynchronizationChainHead(
                requested_device_pseudonym=b"x" * 32, head_event_hash=b"h" * 32
            )
        )
        db.session.commit()
        with pytest.raises(AuditChainVerificationError, match="orphaned"):
            verify_audit()
