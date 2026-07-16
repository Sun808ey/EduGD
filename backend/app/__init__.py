from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Flask

from app.config import get_configuration, resolve_database_uri
from app.errors import register_error_handlers
from app.extensions import db, jwt, migrate
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

    database_uri = resolve_database_uri(configuration)
    if database_uri is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

    if config_overrides:
        app.config.update(config_overrides)

    _validate_database_configuration(app, configuration.DATABASE_ENV_VAR)
    _initialize_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    _register_existing_root_route(app)

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
    migrate.init_app(app, db, compare_type=True)
    jwt.init_app(app)


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
