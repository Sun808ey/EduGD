from flask import Blueprint, Response, current_app, jsonify

from app.services.readiness import check_readiness

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check() -> tuple[Response, int]:
    return (
        jsonify(
            {
                "status": "running",
                "service": "school-policy-api",
            }
        ),
        200,
    )


@health_bp.get("/ready")
def readiness_check() -> tuple[Response, int]:
    try:
        check_readiness(current_app)
    except Exception:  # Readiness must fail closed without exposing internals.
        current_app.logger.warning(
            "Application readiness check failed",
            extra={"event": "readiness_check_failed"},
        )
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "service": "school-policy-api",
                }
            ),
            503,
        )

    return (
        jsonify(
            {
                "status": "ready",
                "service": "school-policy-api",
            }
        ),
        200,
    )
