from flask import Blueprint, Response, current_app, request
from flask_limiter.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.admin_api import admin_error, admin_json
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
from app.services.administrator_login import (
    AdministratorAuthenticationFailed,
    AdministratorLoginDatabaseError,
    authenticate_administrator,
)

auth_bp = Blueprint("auth", __name__)
AUTHORIZATION_SCHEME = "Bearer"


@auth_bp.errorhandler(RateLimitExceeded)
def handle_auth_rate_limit(_error: RateLimitExceeded) -> Response:
    return admin_error("rate_limit_exceeded", "rate limit exceeded", 429)


@auth_bp.post("/admin/auth/login")
@limiter.limit("10 per minute")
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

    return admin_json(
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


@auth_bp.post("/admin/auth/logout")
@administrator_required()
def administrator_logout() -> Response:
    try:
        logout_administrator(get_administrator_request_context())
    except SQLAlchemyError:
        return admin_error("internal_server_error", "internal server error", 500)
    return admin_json({"message": "administrator logged out"}, 200)


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
