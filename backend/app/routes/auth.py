from flask import Blueprint, Response, current_app, request
from flask_limiter.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.admin_api import (
    AdminRequestError,
    admin_error,
    admin_json,
    pagination_payload,
    parse_pagination,
)
from app.administrator_authorization import (
    administrator_permissions,
    administrator_required,
    authentication_failure_response,
    get_administrator_request_context,
    logout_administrator,
)
from app.administrator_schemas import (
    AdministratorLoginValidationError,
    validate_administrator_login_request,
)
from app.extensions import db, limiter
from app.models import ADMINISTRATOR_PERMISSIONS
from app.services.administrator_authentication import (
    AdministratorConflictError,
    AdministratorDatabaseError,
    AdministratorNotFoundError,
    AdministratorOperationError,
    assert_administrator_may_be_disabled,
    authorize_administrator_operator,
    create_administrator,
    disable_administrator,
    get_administrator_by_uuid,
    list_administrators,
    replace_administrator_permissions,
    reset_administrator_password,
    revoke_administrator_sessions,
)
from app.services.administrator_login import (
    AdministratorAuthenticationFailed,
    AdministratorLoginDatabaseError,
    authenticate_administrator,
)

auth_bp = Blueprint("auth", __name__)
AUTHORIZATION_SCHEME = "Bearer"


def _administrator_payload(administrator: object) -> dict[str, object]:
    from app.models import Administrator

    if not isinstance(administrator, Administrator):
        raise TypeError("invalid administrator")
    return {
        "administrator_uuid": str(administrator.administrator_uuid),
        "username": administrator.username,
        "display_name": administrator.display_name,
        "status": administrator.status,
        "permissions": administrator_permissions(administrator.id),
        "created_at": administrator.created_at.isoformat(),
        "password_changed_at": administrator.password_changed_at.isoformat(),
        "disabled_at": (
            administrator.disabled_at.isoformat() if administrator.disabled_at else None
        ),
    }


def _sensitive_payload(*, fields: set[str]) -> dict[str, object] | None:
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        return None
    return payload


def _text(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise ValueError(f"invalid {field}")
    return value


def _administrator_operation_error(error: AdministratorOperationError) -> Response:
    if isinstance(error, AdministratorNotFoundError):
        return admin_error("administrator_not_found", "administrator not found", 404)
    if isinstance(error, AdministratorConflictError):
        return admin_error("administrator_conflict", str(error), 409)
    if isinstance(error, AdministratorDatabaseError):
        return admin_error("internal_server_error", "internal server error", 500)
    if str(error) == "authorized administrator credentials are required":
        return admin_error("authorization_failed", "administrator authorization failed", 403)
    return admin_error("invalid_request", "invalid administrator request", 400)


@auth_bp.errorhandler(RateLimitExceeded)
def handle_auth_rate_limit(_error: RateLimitExceeded) -> Response:
    return admin_error("rate_limit_exceeded", "rate limit exceeded", 429)


@auth_bp.post("/admin/auth/login")
@limiter.limit(lambda: current_app.config["ADMIN_LOGIN_RATE_LIMIT"])
def administrator_login() -> Response:
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    try:
        login_data = validate_administrator_login_request(request)
    except AdministratorLoginValidationError as error:
        return admin_error(
            "invalid_request", "invalid login request", error.status_code
        )

    try:
        result = authenticate_administrator(
            username=login_data.username,
            password=login_data.password,
            source_address=request.remote_addr,
        )
    except AdministratorAuthenticationFailed:
        return authentication_failure_response()
    except AdministratorLoginDatabaseError:
        return admin_error("internal_server_error", "internal server error", 500)

    response = admin_json(
        {
            "access_token": result.access_token,
            "token_type": AUTHORIZATION_SCHEME,
            "expires_in": result.expires_in,
            "administrator": {
                "administrator_uuid": result.administrator_uuid,
                "username": result.username,
                "display_name": result.display_name,
            },
        },
        200,
    )
    return response


@auth_bp.post("/admin/auth/logout")
@administrator_required()
def administrator_logout() -> Response:
    try:
        logout_administrator(get_administrator_request_context())
    except SQLAlchemyError:
        return admin_error("internal_server_error", "internal server error", 500)
    response = admin_json({"message": "administrator logged out"}, 200)
    return response


@auth_bp.get("/admin/auth/me")
@administrator_required()
def administrator_identity() -> Response:
    context = get_administrator_request_context()
    try:
        permissions = administrator_permissions(context.administrator.id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error(
            "Administrator identity lookup failed",
            extra={"event": "administrator_identity_database_error"},
        )
        return admin_error("internal_server_error", "internal server error", 500)

    return admin_json(
        {
            "administrator": {
                "administrator_uuid": str(context.administrator.administrator_uuid),
                "username": context.administrator.username,
                "display_name": context.administrator.display_name,
                "permissions": permissions,
            }
        },
    )


@auth_bp.post("/admin/administrators")
@administrator_required("administrator.manage")
def administrator_create() -> Response:
    """Create a fully privileged administrator from the admin console."""
    request.max_content_length = current_app.config["ADMIN_AUTH_MAX_CONTENT_LENGTH"]
    payload = request.get_json(silent=False)
    fields = {
        "username",
        "display_name",
        "password",
        "operator_password",
        "reason",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        return admin_error("invalid_request", "invalid administrator request", 400)

    context = get_administrator_request_context()
    try:
        result = create_administrator(
            username=payload["username"],
            display_name=payload["display_name"],
            password=payload["password"],
            operator_username=context.administrator.username,
            operator_password=payload["operator_password"],
            operator_subject=f"administrator:{context.administrator.username}",
            reason=payload["reason"],
        )
    except AdministratorConflictError:
        return admin_error(
            "administrator_conflict",
            "administrator username already exists",
            409,
        )
    except AdministratorDatabaseError:
        return admin_error("internal_server_error", "internal server error", 500)
    except AdministratorOperationError as error:
        if str(error) == "authorized administrator credentials are required":
            return admin_error(
                "authorization_failed",
                "administrator authorization failed",
                403,
            )
        return admin_error("invalid_request", "invalid administrator request", 400)
    return admin_json(
        {
            "administrator_uuid": result.administrator_uuid,
            "username": payload["username"],
            "permissions": sorted(ADMINISTRATOR_PERMISSIONS),
            "revoked_sessions": result.revoked_sessions,
        },
        201,
    )


@auth_bp.get("/admin/administrators")
@administrator_required("administrator.manage")
def administrator_list() -> Response:
    try:
        pagination = parse_pagination()
        administrators, total = list_administrators(
            offset=pagination.offset,
            limit=pagination.per_page,
        )
        return admin_json(
            {
                "administrators": [
                    _administrator_payload(administrator)
                    for administrator in administrators
                ],
                "pagination": pagination_payload(pagination, total=total),
            }
        )
    except AdminRequestError:
        return admin_error("invalid_request", "invalid administrator request", 400)
    except AdministratorDatabaseError:
        return admin_error("internal_server_error", "internal server error", 500)


@auth_bp.get("/admin/administrators/<administrator_uuid>")
@administrator_required("administrator.manage")
def administrator_detail(administrator_uuid: str) -> Response:
    try:
        return admin_json(
            {"administrator": _administrator_payload(get_administrator_by_uuid(administrator_uuid))}
        )
    except AdministratorOperationError as error:
        return _administrator_operation_error(error)


@auth_bp.patch("/admin/administrators/<administrator_uuid>/permissions")
@administrator_required("administrator.manage")
def administrator_permissions_replace(administrator_uuid: str) -> Response:
    payload = _sensitive_payload(
        fields={"permissions", "operator_password", "reason"}
    )
    if payload is None:
        return admin_error("invalid_request", "invalid administrator request", 400)
    try:
        context = get_administrator_request_context()
        operator = authorize_administrator_operator(
            operator_username=context.administrator.username,
            operator_password=_text(payload, "operator_password"),
        )
        result = replace_administrator_permissions(
            administrator_uuid=administrator_uuid,
            permissions=payload["permissions"],
            operator=operator,
            operator_subject=f"administrator:{context.administrator.username}",
            reason=_text(payload, "reason"),
        )
        return admin_json(
            {
                "administrator_uuid": result.administrator_uuid,
                "message": "administrator permissions updated",
            }
        )
    except (AdministratorOperationError, ValueError) as error:
        if isinstance(error, ValueError):
            return admin_error("invalid_request", "invalid administrator request", 400)
        return _administrator_operation_error(error)


@auth_bp.post("/admin/administrators/<administrator_uuid>/sessions/revoke")
@administrator_required("administrator.manage")
def administrator_sessions_revoke(administrator_uuid: str) -> Response:
    payload = _sensitive_payload(fields={"operator_password", "reason"})
    if payload is None:
        return admin_error("invalid_request", "invalid administrator request", 400)
    try:
        context = get_administrator_request_context()
        authorize_administrator_operator(
            operator_username=context.administrator.username,
            operator_password=_text(payload, "operator_password"),
        )
        target = get_administrator_by_uuid(administrator_uuid)
        result = revoke_administrator_sessions(
            username=target.username,
            operator_subject=f"administrator:{context.administrator.username}",
            reason=_text(payload, "reason"),
        )
        return admin_json(
            {
                "administrator_uuid": result.administrator_uuid,
                "revoked_sessions": result.revoked_sessions,
            }
        )
    except (AdministratorOperationError, ValueError) as error:
        if isinstance(error, ValueError):
            return admin_error("invalid_request", "invalid administrator request", 400)
        return _administrator_operation_error(error)


@auth_bp.post("/admin/administrators/<administrator_uuid>/disable")
@administrator_required("administrator.manage")
def administrator_disable(administrator_uuid: str) -> Response:
    payload = _sensitive_payload(fields={"operator_password", "reason"})
    if payload is None:
        return admin_error("invalid_request", "invalid administrator request", 400)
    try:
        context = get_administrator_request_context()
        authorize_administrator_operator(
            operator_username=context.administrator.username,
            operator_password=_text(payload, "operator_password"),
        )
        assert_administrator_may_be_disabled(administrator_uuid)
        target = get_administrator_by_uuid(administrator_uuid)
        result = disable_administrator(
            username=target.username,
            operator_subject=f"administrator:{context.administrator.username}",
            reason=_text(payload, "reason"),
        )
        return admin_json(
            {
                "administrator_uuid": result.administrator_uuid,
                "revoked_sessions": result.revoked_sessions,
            }
        )
    except (AdministratorOperationError, ValueError) as error:
        if isinstance(error, ValueError):
            return admin_error("invalid_request", "invalid administrator request", 400)
        return _administrator_operation_error(error)


@auth_bp.post("/admin/administrators/<administrator_uuid>/password/reset")
@administrator_required("administrator.manage")
def administrator_password_reset(administrator_uuid: str) -> Response:
    payload = _sensitive_payload(fields={"password", "operator_password", "reason"})
    if payload is None:
        return admin_error("invalid_request", "invalid administrator request", 400)
    try:
        context = get_administrator_request_context()
        authorize_administrator_operator(
            operator_username=context.administrator.username,
            operator_password=_text(payload, "operator_password"),
        )
        target = get_administrator_by_uuid(administrator_uuid)
        result = reset_administrator_password(
            username=target.username,
            password=_text(payload, "password"),
            operator_subject=f"administrator:{context.administrator.username}",
            reason=_text(payload, "reason"),
        )
        return admin_json(
            {
                "administrator_uuid": result.administrator_uuid,
                "revoked_sessions": result.revoked_sessions,
            }
        )
    except (AdministratorOperationError, ValueError) as error:
        if isinstance(error, ValueError):
            return admin_error("invalid_request", "invalid administrator request", 400)
        return _administrator_operation_error(error)
