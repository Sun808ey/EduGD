from __future__ import annotations

from collections.abc import Mapping
from secrets import token_urlsafe
from typing import Any

from flask import Flask, Response, request
from redis import Redis
from redis.exceptions import RedisError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.administrator_authorization import configure_administrator_jwt
from app.cli import register_cli_commands
from app.config import (
    get_configuration,
    resolve_database_uri,
    resolve_migration_database_uri,
    resolve_production_engine_options,
    validate_database_separation,
    validate_migration_target,
)
from app.errors import register_error_handlers
from app.extensions import db, jwt, limiter, migrate
from app.observability import configure_sentry, configure_structured_logging
from app.routes import BLUEPRINTS


def create_app(
    config_name: str | None = None,
    config_overrides: Mapping[str, Any] | None = None,
) -> Flask:
    """Create and configure an application instance."""
    app = Flask(__name__)

    selected_name, configuration = get_configuration(config_name)
    app.config.from_object(configuration)
    app.config["APP_ENV"] = selected_name

    if selected_name == "production":
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = resolve_production_engine_options()

    database_uri = resolve_database_uri(configuration)
    if database_uri is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

    if config_overrides:
        app.config.update(config_overrides)

    _apply_nonproduction_secret_defaults(app)
    configure_structured_logging(app)
    _validate_database_configuration(app, configuration.DATABASE_ENV_VAR)
    validate_database_separation()
    migration_database_uri = resolve_migration_database_uri(
        selected_name,
        app.config.get("SQLALCHEMY_DATABASE_URI"),
    )
    app.config["MIGRATION_DATABASE_URI"] = migration_database_uri
    if selected_name != "testing" and migration_database_uri is not None:
        validate_migration_target(
            app.config["SQLALCHEMY_DATABASE_URI"],
            migration_database_uri,
        )
    _validate_startup_configuration(app)
    _configure_trusted_proxy(app)
    configure_sentry(app)
    _initialize_extensions(app)
    _configure_admin_cors(app)
    configure_administrator_jwt()
    register_cli_commands(app)
    register_blueprints(app)
    register_error_handlers(app)
    _register_existing_root_route(app)
    app.logger.info(
        "Application startup completed",
        extra={"event": "application_startup"},
    )

    return app


def _validate_database_configuration(
    app: Flask,
    database_environment_variable: str | None,
) -> None:
    if app.config.get("SQLALCHEMY_DATABASE_URI"):
        return

    variable_name = database_environment_variable or "SQLALCHEMY_DATABASE_URI"
    raise RuntimeError(
        f"{variable_name} must be configured for the "
        f"{app.config['APP_ENV']} environment"
    )


def _initialize_extensions(app: Flask) -> None:
    db.init_app(app)
    _load_models()
    migrate.init_app(app, db, compare_type=True)
    jwt.init_app(app)
    limiter.init_app(app)


def _apply_nonproduction_secret_defaults(app: Flask) -> None:
    if app.config["APP_ENV"] == "production":
        return
    for setting in (
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "ADMIN_AUDIT_PSEUDONYM_KEY",
        "POLICY_SYNC_AUDIT_KEY",
    ):
        if not app.config.get(setting):
            app.config[setting] = token_urlsafe(32)


def _validate_startup_configuration(app: Flask) -> None:
    enrollment_mode = app.config["DEVICE_ENROLLMENT_MODE"]
    if enrollment_mode not in {"legacy", "new_devices_required", "all_required"}:
        raise RuntimeError("DEVICE_ENROLLMENT_MODE is invalid")
    if (app.config["ENROLLMENT_ADMIN_ENABLED"] or enrollment_mode != "legacy") and (
        not isinstance(app.config.get("PAIRING_TOKEN_PEPPER"), str)
        or len(app.config["PAIRING_TOKEN_PEPPER"]) < 32
    ):
        raise RuntimeError("PAIRING_TOKEN_PEPPER must contain at least 32 characters")
    if app.config["PAIRING_TOKEN_PEPPER_VERSION"] < 1:
        raise RuntimeError("PAIRING_TOKEN_PEPPER_VERSION must be positive")

    if app.config["APP_ENV"] != "production":
        return

    required_settings = (
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "ADMIN_AUDIT_PSEUDONYM_KEY",
        "POLICY_SYNC_AUDIT_KEY",
    )
    if any(not app.config.get(setting) for setting in required_settings):
        raise RuntimeError("Required production secrets must be configured")
    if any(
        not isinstance(app.config[setting], str) or len(app.config[setting]) < 32
        for setting in required_settings
    ):
        raise RuntimeError("Production secrets must be at least 32 characters")
    if len({app.config[setting] for setting in required_settings}) != len(
        required_settings
    ):
        raise RuntimeError("Production secrets must be distinct")
    pairing_pepper = app.config.get("PAIRING_TOKEN_PEPPER")
    if pairing_pepper and pairing_pepper in {
        app.config[setting] for setting in required_settings
    }:
        raise RuntimeError("Production secrets must be distinct")
    if app.config["DEBUG"] or app.config["TESTING"]:
        raise RuntimeError("Production startup cannot enable debug or testing mode")
    storage_uri = app.config.get("RATELIMIT_STORAGE_URI")
    if not isinstance(storage_uri, str) or not storage_uri.startswith(
        ("redis://", "rediss://")
    ):
        raise RuntimeError("Production rate limiting requires REDIS_URL")
    try:
        Redis.from_url(
            storage_uri,
            socket_connect_timeout=3,
            socket_timeout=3,
        ).ping()
    except (RedisError, ValueError, OSError):
        raise RuntimeError("Production rate-limit storage is unavailable") from None


def _configure_trusted_proxy(app: Flask) -> None:
    hops = app.config.get("TRUSTED_PROXY_HOPS", 0)
    if hops == 0:
        return
    if app.config["APP_ENV"] != "production" or hops != 1:
        raise RuntimeError("Trusted proxy configuration is invalid")
    app.wsgi_app = ProxyFix(  # type: ignore[method-assign]
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
    )


def _configure_admin_cors(app: Flask) -> None:
    allowed_origins = _admin_frontend_origins(app)
    if app.config["APP_ENV"] == "production" and not allowed_origins:
        raise RuntimeError("Production CORS requires ADMIN_FRONTEND_ORIGINS")

    @app.before_request
    def reject_disallowed_admin_preflight() -> tuple[str, int] | None:
        if request.method != "OPTIONS" or not request.path.startswith("/api/v1/admin/"):
            return None
        origin = request.headers.get("Origin")
        requested_method = request.headers.get("Access-Control-Request-Method")
        if origin is None or requested_method is None:
            return None
        if origin not in allowed_origins:
            return "", 403
        return "", 204

    @app.after_request
    def add_admin_cors_headers(response: Response) -> Response:
        if not request.path.startswith("/api/v1/admin/"):
            return response
        origin = request.headers.get("Origin")
        if origin not in allowed_origins:
            return response
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = _append_vary(response.headers.get("Vary"), "Origin")
        return response


def _admin_frontend_origins(app: Flask) -> frozenset[str]:
    raw_origins = app.config.get("ADMIN_FRONTEND_ORIGINS", "")
    if not isinstance(raw_origins, str):
        raise RuntimeError("ADMIN_FRONTEND_ORIGINS must be a comma-separated string")
    origins = frozenset(
        origin.strip() for origin in raw_origins.split(",") if origin.strip()
    )
    if "*" in origins:
        raise RuntimeError("ADMIN_FRONTEND_ORIGINS cannot contain a wildcard")
    return origins


def _append_vary(current: str | None, value: str) -> str:
    if not current:
        return value
    existing = [part.strip() for part in current.split(",")]
    if value in existing:
        return current
    return f"{current}, {value}"


def _load_models() -> None:
    from app.models import (
        Administrator,
        AdministratorAuthenticationEvent,
        AdministratorPermission,
        AdministratorSession,
        Device,
        DeviceCredential,
        DeviceEnrollmentEvent,
        DevicePolicyAssignment,
        DeviceRegistrationEvent,
        DeviceRequestNonce,
        EnrollmentToken,
        Policy,
        PolicyAssignmentChainHead,
        PolicyAssignmentEvent,
        PolicyRevision,
        PolicySynchronizationChainHead,
        PolicySynchronizationEvent,
    )

    _ = (
        Administrator,
        AdministratorAuthenticationEvent,
        AdministratorPermission,
        AdministratorSession,
        Device,
        DeviceCredential,
        DeviceEnrollmentEvent,
        DevicePolicyAssignment,
        DeviceRegistrationEvent,
        DeviceRequestNonce,
        EnrollmentToken,
        Policy,
        PolicyAssignmentChainHead,
        PolicyAssignmentEvent,
        PolicyRevision,
        PolicySynchronizationChainHead,
        PolicySynchronizationEvent,
    )


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix="/api/v1")


def _register_existing_root_route(app: Flask) -> None:
    @app.get("/")
    def home() -> dict[str, str]:
        return {
            "system": "School Policy Enforcement API",
            "status": "running",
        }
