from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Never

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    ADMINISTRATOR_PERMISSIONS,
    ADMINISTRATOR_USERNAME_PATTERN,
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    AdministratorSession,
    utc_now,
)

MINIMUM_ADMINISTRATOR_PASSWORD_LENGTH = 12
MAXIMUM_ADMINISTRATOR_PASSWORD_LENGTH = 128
PLACEHOLDER_PASSWORDS = frozenset(
    {
        "administrator",
        "changemechangeme",
        "password1234",
        "passwordpassword",
    }
)


@dataclass(frozen=True, slots=True)
class AdministratorMutationResult:
    administrator_uuid: str
    revoked_sessions: int = 0


class AdministratorOperationError(RuntimeError):
    pass


class AdministratorConflictError(AdministratorOperationError):
    pass


class AdministratorNotFoundError(AdministratorOperationError):
    pass


class AdministratorDatabaseError(AdministratorOperationError):
    pass


def bootstrap_administrator(
    *,
    username: str,
    display_name: str,
    password: str,
    operator_subject: str,
    reason: str,
) -> AdministratorMutationResult:
    username = _validate_username(username)
    display_name = _validate_printable_text(display_name, "display name", 120)
    operator_subject = _validate_printable_text(
        operator_subject,
        "operator subject",
        255,
    )
    reason = _validate_printable_text(reason, "reason", 512)
    _validate_password(password, username)

    try:
        existing_id = db.session.execute(
            select(Administrator.id).limit(1)
        ).scalar_one_or_none()
        if existing_id is not None:
            raise AdministratorConflictError(
                "administrator bootstrap has already been completed"
            )

        administrator = Administrator(
            username=username,
            display_name=display_name,
            password_verifier=_hash_password(password),
        )
        db.session.add(administrator)
        db.session.flush()

        for permission in sorted(ADMINISTRATOR_PERMISSIONS):
            db.session.add(
                AdministratorPermission(
                    administrator_id=administrator.id,
                    permission=permission,
                    trusted_operator_subject=operator_subject,
                    reason=reason,
                )
            )
        db.session.add(
            AdministratorAuthenticationEvent(
                administrator_id=administrator.id,
                category="bootstrap",
                trusted_operator_subject=operator_subject,
                reason=reason,
            )
        )
        administrator_uuid = str(administrator.administrator_uuid)
        db.session.commit()
        _log_outcome("administrator_bootstrap_completed")
        return AdministratorMutationResult(administrator_uuid=administrator_uuid)
    except AdministratorOperationError:
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        raise AdministratorConflictError(
            "administrator bootstrap could not be completed"
        ) from error
    except SQLAlchemyError as error:
        _raise_database_error(error, "administrator_bootstrap_database_error")


def reset_administrator_password(
    *,
    username: str,
    password: str,
    operator_subject: str,
    reason: str,
) -> AdministratorMutationResult:
    username = _validate_username(username)
    operator_subject, reason = _validate_operator_context(operator_subject, reason)
    _validate_password(password, username)

    try:
        administrator = _find_administrator(username)
        now = utc_now()
        administrator.password_verifier = _hash_password(password)
        administrator.password_changed_at = now
        administrator.failed_attempts = 0
        administrator.lock_expires_at = None
        if administrator.status == "locked":
            administrator.status = "active"
        administrator.updated_at = now
        revoked_sessions = _revoke_active_sessions(
            administrator.id,
            now,
            operator_subject,
            reason,
        )
        _add_operator_event(
            administrator.id,
            "password_reset",
            operator_subject,
            reason,
        )
        administrator_uuid = str(administrator.administrator_uuid)
        db.session.commit()
        _log_outcome("administrator_password_reset_completed")
        return AdministratorMutationResult(
            administrator_uuid=administrator_uuid,
            revoked_sessions=revoked_sessions,
        )
    except AdministratorOperationError:
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        _raise_database_error(error, "administrator_password_reset_database_error")


def disable_administrator(
    *,
    username: str,
    operator_subject: str,
    reason: str,
) -> AdministratorMutationResult:
    username = _validate_username(username)
    operator_subject, reason = _validate_operator_context(operator_subject, reason)

    try:
        administrator = _find_administrator(username)
        if administrator.status == "disabled":
            raise AdministratorConflictError("administrator is already disabled")

        now = utc_now()
        administrator.status = "disabled"
        administrator.disabled_at = now
        administrator.lock_expires_at = None
        administrator.updated_at = now
        revoked_sessions = _revoke_active_sessions(
            administrator.id,
            now,
            operator_subject,
            reason,
        )
        _add_operator_event(
            administrator.id,
            "account_disabled",
            operator_subject,
            reason,
        )
        administrator_uuid = str(administrator.administrator_uuid)
        db.session.commit()
        _log_outcome("administrator_disable_completed")
        return AdministratorMutationResult(
            administrator_uuid=administrator_uuid,
            revoked_sessions=revoked_sessions,
        )
    except AdministratorOperationError:
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        _raise_database_error(error, "administrator_disable_database_error")


def revoke_administrator_sessions(
    *,
    username: str,
    operator_subject: str,
    reason: str,
) -> AdministratorMutationResult:
    username = _validate_username(username)
    operator_subject, reason = _validate_operator_context(operator_subject, reason)

    try:
        administrator = _find_administrator(username)
        now = utc_now()
        revoked_sessions = _revoke_active_sessions(
            administrator.id,
            now,
            operator_subject,
            reason,
        )
        _add_operator_event(
            administrator.id,
            "session_revoked",
            operator_subject,
            reason,
        )
        administrator_uuid = str(administrator.administrator_uuid)
        db.session.commit()
        _log_outcome("administrator_sessions_revoked")
        return AdministratorMutationResult(
            administrator_uuid=administrator_uuid,
            revoked_sessions=revoked_sessions,
        )
    except AdministratorOperationError:
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        _raise_database_error(error, "administrator_session_revoke_database_error")


def _find_administrator(username: str) -> Administrator:
    administrator = db.session.execute(
        select(Administrator).where(Administrator.username == username)
    ).scalar_one_or_none()
    if administrator is None:
        raise AdministratorNotFoundError("administrator was not found")
    return administrator


def _revoke_active_sessions(
    administrator_id: int,
    now: datetime,
    operator_subject: str,
    reason: str,
) -> int:
    sessions = db.session.execute(
        select(AdministratorSession).where(
            AdministratorSession.administrator_id == administrator_id,
            AdministratorSession.revoked_at.is_(None),
            AdministratorSession.expires_at > now,
        )
    ).scalars()
    revoked_count = 0
    for session in sessions:
        session.revoked_at = now
        session.revoked_by_operator_subject = operator_subject
        session.revocation_reason = reason
        revoked_count += 1
    return revoked_count


def _add_operator_event(
    administrator_id: int,
    category: str,
    operator_subject: str,
    reason: str,
) -> None:
    db.session.add(
        AdministratorAuthenticationEvent(
            administrator_id=administrator_id,
            category=category,
            trusted_operator_subject=operator_subject,
            reason=reason,
        )
    )


def _hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def _validate_password(password: object, username: str) -> str:
    if not isinstance(password, str) or not (
        MINIMUM_ADMINISTRATOR_PASSWORD_LENGTH
        <= len(password)
        <= MAXIMUM_ADMINISTRATOR_PASSWORD_LENGTH
    ):
        raise AdministratorOperationError(
            "administrator password must contain 12 to 128 characters"
        )
    if password.casefold() in PLACEHOLDER_PASSWORDS or password.casefold() == username:
        raise AdministratorOperationError("administrator password is not permitted")
    return password


def _validate_username(username: object) -> str:
    if not isinstance(username, str) or not ADMINISTRATOR_USERNAME_PATTERN.fullmatch(
        username
    ):
        raise AdministratorOperationError("invalid administrator username")
    return username


def _validate_operator_context(
    operator_subject: object,
    reason: object,
) -> tuple[str, str]:
    return (
        _validate_printable_text(operator_subject, "operator subject", 255),
        _validate_printable_text(reason, "reason", 512),
    )


def _validate_printable_text(value: object, field: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or not value.isprintable()
    ):
        raise AdministratorOperationError(
            f"{field} must contain 1 to {maximum} printable characters"
        )
    return value


def _log_outcome(event_name: str) -> None:
    current_app.logger.info(
        "Administrator CLI operation completed",
        extra={"event": event_name},
    )


def _raise_database_error(error: SQLAlchemyError, event_name: str) -> Never:
    db.session.rollback()
    current_app.logger.error(
        "Administrator CLI database operation failed",
        extra={"event": event_name},
    )
    raise AdministratorDatabaseError(
        "administrator database operation failed"
    ) from error


__all__ = [
    "AdministratorConflictError",
    "AdministratorDatabaseError",
    "AdministratorMutationResult",
    "AdministratorNotFoundError",
    "AdministratorOperationError",
    "bootstrap_administrator",
    "disable_administrator",
    "reset_administrator_password",
    "revoke_administrator_sessions",
]
