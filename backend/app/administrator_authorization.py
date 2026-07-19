from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from typing import Any, cast

from flask import Response, current_app, g, jsonify, request
from flask.typing import ResponseReturnValue
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, jwt
from app.models import (
    Administrator,
    AdministratorAuthenticationEvent,
    AdministratorPermission,
    AdministratorSession,
    utc_now,
)
from app.services.administrator_login import (
    AdministratorLoginDatabaseError,
    digest_jti,
    pseudonymize_source_address,
)


@dataclass(frozen=True, slots=True)
class AdministratorRequestContext:
    administrator: Administrator
    session: AdministratorSession


class AdministratorSessionError(RuntimeError):
    def __init__(
        self,
        failure_class: str,
        administrator: Administrator | None = None,
        session: AdministratorSession | None = None,
    ) -> None:
        super().__init__("administrator session authentication failed")
        self.failure_class = failure_class
        self.administrator = administrator
        self.session = session


def configure_administrator_jwt() -> None:
    @jwt.unauthorized_loader
    def missing_token(_reason: str) -> Response:
        _record_unverified_authentication_failure("missing_token")
        return authentication_failure_response()

    @jwt.invalid_token_loader
    def invalid_token(_reason: str) -> Response:
        _record_unverified_authentication_failure("invalid_token")
        return authentication_failure_response()

    @jwt.expired_token_loader
    def expired_token(_header: dict[str, Any], _claims: dict[str, Any]) -> Response:
        _record_unverified_authentication_failure("expired_token")
        return authentication_failure_response()

    @jwt.needs_fresh_token_loader
    def nonfresh_token(_header: dict[str, Any], _claims: dict[str, Any]) -> Response:
        _record_unverified_authentication_failure("invalid_token")
        return authentication_failure_response()

    @jwt.revoked_token_loader
    def revoked_token(_header: dict[str, Any], _claims: dict[str, Any]) -> Response:
        _record_unverified_authentication_failure("revoked_session")
        return authentication_failure_response()

    @jwt.token_verification_failed_loader
    def verification_failed(
        _header: dict[str, Any],
        _claims: dict[str, Any],
    ) -> Response:
        _record_unverified_authentication_failure("invalid_token")
        return authentication_failure_response()


def administrator_required[**P](
    permission: str | None = None,
) -> Callable[
    [Callable[P, ResponseReturnValue]],
    Callable[P, ResponseReturnValue],
]:
    def decorator(
        function: Callable[P, ResponseReturnValue],
    ) -> Callable[P, ResponseReturnValue]:
        @jwt_required()
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
            try:
                context = _load_current_administrator_context()
                if permission is not None and not _has_permission(
                    context.administrator.id,
                    permission,
                ):
                    _record_authorization_failure(
                        "permission_denied",
                        context.administrator,
                        context.session,
                        acting_administrator=context.administrator,
                    )
                    return authorization_failure_response()
                g.administrator_request_context = context
            except AdministratorSessionError as error:
                _record_authorization_failure(
                    error.failure_class,
                    error.administrator,
                    error.session,
                )
                return authentication_failure_response()
            except (AdministratorLoginDatabaseError, SQLAlchemyError):
                db.session.rollback()
                current_app.logger.error(
                    "Administrator session validation failed closed",
                    extra={"event": "administrator_session_database_error"},
                )
                return authentication_failure_response()
            return function(*args, **kwargs)

        return cast(Callable[P, ResponseReturnValue], wrapped)

    return decorator


def get_administrator_request_context() -> AdministratorRequestContext:
    return cast(
        AdministratorRequestContext,
        g.administrator_request_context,
    )


def logout_administrator(context: AdministratorRequestContext) -> None:
    now = utc_now()
    context.session.revoked_at = now
    context.session.revoked_by_administrator_id = context.administrator.id
    context.session.revocation_reason = "administrator logout"
    db.session.add(
        AdministratorAuthenticationEvent(
            administrator_id=context.administrator.id,
            session_id=context.session.id,
            category="logout",
            acting_administrator_id=context.administrator.id,
            reason="administrator logout",
        )
    )
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error(
            "Administrator logout database operation failed",
            extra={"event": "administrator_logout_database_error"},
        )
        raise


def administrator_permissions(administrator_id: int) -> list[str]:
    return list(
        db.session.execute(
            select(AdministratorPermission.permission)
            .where(AdministratorPermission.administrator_id == administrator_id)
            .order_by(AdministratorPermission.permission)
        ).scalars()
    )


def authentication_failure_response() -> Response:
    return _no_store_response("authentication_failed", 401)


def authorization_failure_response() -> Response:
    return _no_store_response("authorization_failed", 403)


def _load_current_administrator_context() -> AdministratorRequestContext:
    claims = get_jwt()
    jti = claims.get("jti")
    subject = claims.get("sub")
    if (
        not isinstance(jti, str)
        or not 1 <= len(jti) <= 128
        or not isinstance(subject, str)
        or not 1 <= len(subject) <= 64
    ):
        raise AdministratorSessionError("invalid_session")

    row = db.session.execute(
        select(AdministratorSession, Administrator)
        .join(
            Administrator,
            Administrator.id == AdministratorSession.administrator_id,
        )
        .where(AdministratorSession.jti_digest == digest_jti(jti))
    ).one_or_none()
    if row is None:
        raise AdministratorSessionError("invalid_session")

    session, administrator = row
    if subject != str(administrator.administrator_uuid):
        raise AdministratorSessionError(
            "invalid_session",
            administrator,
            session,
        )
    if session.revoked_at is not None:
        raise AdministratorSessionError(
            "revoked_session",
            administrator,
            session,
        )
    if _as_utc(session.expires_at) <= utc_now():
        raise AdministratorSessionError(
            "expired_session",
            administrator,
            session,
        )
    if administrator.status == "disabled":
        raise AdministratorSessionError(
            "account_disabled",
            administrator,
            session,
        )
    if administrator.status == "locked":
        raise AdministratorSessionError(
            "account_locked",
            administrator,
            session,
        )
    if administrator.status != "active":
        raise AdministratorSessionError(
            "invalid_session",
            administrator,
            session,
        )
    return AdministratorRequestContext(administrator, session)


def _has_permission(administrator_id: int, permission: str) -> bool:
    return (
        db.session.execute(
            select(AdministratorPermission.id).where(
                AdministratorPermission.administrator_id == administrator_id,
                AdministratorPermission.permission == permission,
            )
        ).scalar_one_or_none()
        is not None
    )


def _record_authorization_failure(
    failure_class: str,
    administrator: Administrator | None,
    session: AdministratorSession | None,
    *,
    acting_administrator: Administrator | None = None,
) -> None:
    try:
        db.session.add(
            AdministratorAuthenticationEvent(
                administrator_id=(administrator.id if administrator else None),
                session_id=(session.id if session else None),
                category="authorization_failed",
                failure_class=failure_class,
                source_address_pseudonym=pseudonymize_source_address(
                    request.remote_addr
                ),
                acting_administrator_id=(
                    acting_administrator.id if acting_administrator else None
                ),
            )
        )
        db.session.commit()
    except (AdministratorLoginDatabaseError, SQLAlchemyError):
        db.session.rollback()
        current_app.logger.error(
            "Administrator authorization event could not be recorded",
            extra={"event": "administrator_authorization_event_error"},
        )


def _record_unverified_authentication_failure(failure_class: str) -> None:
    try:
        db.session.add(
            AdministratorAuthenticationEvent(
                category="authorization_failed",
                failure_class=failure_class,
                source_address_pseudonym=pseudonymize_source_address(
                    request.remote_addr
                ),
            )
        )
        db.session.commit()
    except (AdministratorLoginDatabaseError, SQLAlchemyError):
        db.session.rollback()
        current_app.logger.error(
            "Unverified administrator authentication event could not be recorded",
            extra={"event": "administrator_unverified_authentication_event_error"},
        )


def _no_store_response(error: str, status_code: int) -> Response:
    response = jsonify({"error": error})
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "AdministratorRequestContext",
    "administrator_permissions",
    "administrator_required",
    "authentication_failure_response",
    "authorization_failure_response",
    "configure_administrator_jwt",
    "get_administrator_request_context",
    "logout_administrator",
]
