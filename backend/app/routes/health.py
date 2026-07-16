from flask import Blueprint, Response, jsonify


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
