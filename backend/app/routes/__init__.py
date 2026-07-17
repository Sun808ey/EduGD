from flask import Blueprint

from app.routes.auth import auth_bp
from app.routes.devices import device_bp
from app.routes.health import health_bp
from app.routes.logs import logs_bp
from app.routes.policies import policy_bp
from app.routes.sync import sync_bp

BLUEPRINTS: tuple[Blueprint, ...] = (
    health_bp,
    auth_bp,
    device_bp,
    policy_bp,
    sync_bp,
    logs_bp,
)

__all__ = ["BLUEPRINTS"]
