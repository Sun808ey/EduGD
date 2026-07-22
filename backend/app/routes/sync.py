from flask import Blueprint, Response, jsonify, request

from app.extensions import limiter
from app.services.device_authentication import (
    credential_rate_limit_key,
    device_authentication_required,
)
from app.services.policy_sync import (
    DeviceBlockedError,
    DeviceNotFoundError,
    InvalidCurrentVersionError,
    InvalidDeviceUUIDError,
    get_policy_sync_payload,
    get_version_aware_policy_sync_payload,
)

sync_bp = Blueprint("sync", __name__)


@sync_bp.get("/sync/policies/<device_uuid>")
@device_authentication_required(allowed_query_names=frozenset({"current_version"}))
@limiter.limit("60 per minute", key_func=credential_rate_limit_key)
def synchronize_policy(device_uuid: str) -> tuple[Response, int]:
    try:
        current_version = _parse_current_version()
        if current_version is None:
            payload = get_policy_sync_payload(device_uuid)
        else:
            payload = get_version_aware_policy_sync_payload(
                device_uuid,
                current_version,
            )
    except InvalidCurrentVersionError:
        return jsonify({"error": "current_version must be a non-negative integer"}), 400
    except InvalidDeviceUUIDError:
        return jsonify({"error": "invalid device UUID"}), 400
    except DeviceNotFoundError:
        return jsonify({"error": "device not found"}), 404
    except DeviceBlockedError:
        return (
            jsonify(
                {
                    "error": "device is not active",
                    "operation": "blocked",
                }
            ),
            403,
        )

    return jsonify(payload), 200


def _parse_current_version() -> int | None:
    values = request.args.getlist("current_version")
    if not values:
        return None

    if len(values) != 1:
        raise InvalidCurrentVersionError()

    value = values[0]
    if not value or not value.isascii() or not value.isdigit():
        raise InvalidCurrentVersionError()

    return int(value)
