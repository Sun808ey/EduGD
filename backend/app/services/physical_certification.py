"""Persist only verifier-signed, dual-approved immutable certification records."""

from __future__ import annotations

import json
from hashlib import sha256

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import DeviceCapabilityCertification
from app.physical_certification import CertificationError, verify_certification_record
from app.policy_contract import canonical_json_bytes


def store_certification(
    record: object,
    *,
    verifier_key: Ed25519PublicKey,
    operator_keys: dict[str, Ed25519PublicKey],
) -> DeviceCapabilityCertification:
    verified = verify_certification_record(
        record, verifier_key=verifier_key, operator_keys=operator_keys
    )
    payload = verified["payload"]
    try:
        # Serialize before insertion so caller mutation cannot change evidence.
        immutable_record = json.loads(canonical_json_bytes(verified))
        if db.session.get_bind().dialect.name == "postgresql":
            db.session.execute(text("SELECT pg_advisory_xact_lock(1822053011)"))
        latest = db.session.execute(
            select(DeviceCapabilityCertification)
            .order_by(DeviceCapabilityCertification.id.desc())
            .limit(1)
            .with_for_update()
        ).scalar_one_or_none()
        previous = latest.record_hash if latest else None
        expected = previous.hex() if previous else None
        if payload["previous_record_hash"] != expected:
            raise CertificationError("certification chain head changed")
        stored = DeviceCapabilityCertification(
            build_fingerprint=payload["identity"]["build_fingerprint"],
            record=immutable_record,
            record_hash=sha256(canonical_json_bytes(immutable_record)).digest(),
            previous_record_hash=previous,
        )
        db.session.add(stored)
        db.session.commit()
        return stored
    except (CertificationError, SQLAlchemyError):
        db.session.rollback()
        raise
