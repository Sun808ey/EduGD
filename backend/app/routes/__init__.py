from flask import Blueprint

from app.routes.auth import auth_bp
from app.routes.device_audit import device_audit_bp
from app.routes.devices import device_bp
from app.routes.dpc_controls import dpc_controls_bp
from app.routes.enrollment import enrollment_bp
from app.routes.health import health_bp
from app.routes.logs import logs_bp
from app.routes.managed_applications import managed_application_bp
from app.routes.policies import policy_bp
from app.routes.sync import sync_bp
from app.routes.translation import translation_bp

BLUEPRINTS: tuple[Blueprint, ...] = (
    health_bp,
    auth_bp,
    device_bp,
    dpc_controls_bp,
    device_audit_bp,
    enrollment_bp,
    policy_bp,
    managed_application_bp,
    sync_bp,
    translation_bp,
    logs_bp,
)

__all__ = ["BLUEPRINTS"]
