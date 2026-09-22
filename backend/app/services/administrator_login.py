from __future__ import annotations

import hashlib
import hmac
import ipaddress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Never

from flask import current_app
from flask_jwt_extended import create_access_token, decode_token
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import (
    ADMINISTRATOR_USERNAME_PATTERN,
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorSession,
    utc_now,
)

ADMINISTRATOR_LOCK_DURATION = timedelta(minutes=15)
_DUMMY_PASSWORD_VERIFIER = generate_password_hash(
    token_urlsafe(32),
    method="scrypt",
)


@dataclass(frozen=True, slots=True)
class AdministratorLoginResult:
    access_token: str
    expires_in: int
    administrator_uuid: str
    username: str
    display_name: str


class AdministratorLoginError(RuntimeError):
    pass


class AdministratorAuthenticationFailed(AdministratorLoginError):
    pass


class AdministratorLoginDatabaseError(AdministratorLoginError):
    pass


def authenticate_administrator(
    *,
    username: str,
    password: str,
    source_address: str | None,
) -> AdministratorLoginResult:
    source_pseudonym = pseudonymize_source_address(source_address)
    canonical_username = (
        username if ADMINISTRATOR_USERNAME_PATTERN.fullmatch(username) else None
    )

    try:
        administrator = None
        if canonical_username is not None:
            administrator = db.session.execute(
                select(Administrator)
                .where(Administrator.username == canonical_username)
                .with_for_update()
            ).scalar_one_or_none()

        verifier = (
            administrator.password_verifier
            if administrator is not None
            else _DUMMY_PASSWORD_VERIFIER
        )
        password_valid = _check_password(verifier, password)
        now = utc_now()

        if administrator is None:
            _record_login_failure(None, source_pseudonym, "invalid_credentials")
            db.session.commit()
            raise AdministratorAuthenticationFailed("authentication failed")

        if administrator.status == "disabled":
            _record_login_failure(
                administrator.id,
                source_pseudonym,
                "account_disabled",
            )
            db.session.commit()
            raise AdministratorAuthenticationFailed("authentication failed")

        if administrator.status == "locked":
            lock_active = _as_utc(administrator.lock_expires_at) > now
            if lock_active or not password_valid:
                if not lock_active:
                    administrator.lock_expires_at = now + ADMINISTRATOR_LOCK_DURATION
                    administrator.updated_at = now
                _record_login_failure(
                    administrator.id,
                    source_pseudonym,
                    "account_locked",
                )
                db.session.commit()
                raise AdministratorAuthenticationFailed("authentication failed")

            administrator.status = "active"
            administrator.failed_attempts = 0
            administrator.lock_expires_at = None
            administrator.updated_at = now
            db.session.add(
                AdministratorAuthenticationEvent(
                    administrator_id=administrator.id,
                    category="account_unlocked",
                    source_address_pseudonym=source_pseudonym,
                )
            )

        elif not password_valid:
            administrator.failed_attempts += 1
            administrator.updated_at = now
            _record_login_failure(
                administrator.id,
                source_pseudonym,
                "invalid_credentials",
            )
            if administrator.failed_attempts == 5:
                administrator.status = "locked"
                administrator.lock_expires_at = now + ADMINISTRATOR_LOCK_DURATION
                db.session.add(
                    AdministratorAuthenticationEvent(
                        administrator_id=administrator.id,
                        category="account_locked",
                        source_address_pseudonym=source_pseudonym,
                    )
                )
            db.session.commit()
            raise AdministratorAuthenticationFailed("authentication failed")

        administrator.failed_attempts = 0
        administrator.updated_at = now
        access_token = create_access_token(
            identity=str(administrator.administrator_uuid)
        )
        claims = decode_token(access_token)
        issued_at = datetime.fromtimestamp(int(claims["iat"]), UTC)
        expires_at = datetime.fromtimestamp(int(claims["exp"]), UTC)
        session = AdministratorSession(
            administrator_id=administrator.id,
            jti_digest=digest_jti(str(claims["jti"])),
            source_address_pseudonym=source_pseudonym,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        db.session.add(session)
        db.session.flush()
        db.session.add(
            AdministratorAuthenticationEvent(
                administrator_id=administrator.id,
                session_id=session.id,
                category="login_succeeded",
                source_address_pseudonym=source_pseudonym,
            )
        )
        result = AdministratorLoginResult(
            access_token=access_token,
            expires_in=int((expires_at - issued_at).total_seconds()),
            administrator_uuid=str(administrator.administrator_uuid),
            username=administrator.username,
            display_name=administrator.display_name,
        )
        db.session.commit()
        _log_outcome("administrator_login_succeeded")
        return result
    except AdministratorAuthenticationFailed:
        db.session.rollback()
        _log_outcome("administrator_login_failed")
        raise
    except AdministratorLoginDatabaseError:
        db.session.rollback()
        current_app.logger.error(
            "Administrator authentication verifier operation failed",
            extra={"event": "administrator_login_verifier_error"},
        )
        raise
    except SQLAlchemyError as error:
        _raise_database_error(error)


def pseudonymize_source_address(source_address: str | None) -> bytes:
    key = current_app.config.get("ADMIN_AUDIT_PSEUDONYM_KEY")
    if not isinstance(key, str) or len(key) < 32:
        raise AdministratorLoginDatabaseError(
            "administrator authentication configuration is unavailable"
        )
    canonical_source = "unavailable"
    if source_address is not None:
        try:
            canonical_source = ipaddress.ip_address(source_address).compressed
        except ValueError:
            canonical_source = "unavailable"
    return hmac.digest(
        key.encode("utf-8"),
        canonical_source.encode("ascii"),
        "sha256",
    )


def digest_jti(jti: str) -> bytes:
    return hashlib.sha256(jti.encode("utf-8")).digest()


def _record_login_failure(
    administrator_id: int | None,
    source_pseudonym: bytes,
    failure_class: str,
) -> None:
    db.session.add(
        AdministratorAuthenticationEvent(
            administrator_id=administrator_id,
            category="login_failed",
            failure_class=failure_class,
            source_address_pseudonym=source_pseudonym,
        )
    )


def _check_password(verifier: str, password: str) -> bool:
    try:
        return check_password_hash(verifier, password)
    except ValueError as error:
        raise AdministratorLoginDatabaseError(
            "administrator credential verifier is invalid"
        ) from error


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _log_outcome(event_name: str) -> None:
    current_app.logger.info(
        "Administrator authentication outcome",
        extra={"event": event_name},
    )


def _raise_database_error(error: SQLAlchemyError) -> Never:
    db.session.rollback()
    current_app.logger.error(
        "Administrator authentication database operation failed",
        extra={"event": "administrator_login_database_error"},
    )
    raise AdministratorLoginDatabaseError(
        "administrator authentication database operation failed"
    ) from error


__all__ = [
    "AdministratorAuthenticationFailed",
    "AdministratorLoginDatabaseError",
    "AdministratorLoginResult",
    "authenticate_administrator",
    "digest_jti",
    "pseudonymize_source_address",
]
