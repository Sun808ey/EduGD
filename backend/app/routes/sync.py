from flask import Blueprint, Response, jsonify

from app.services.policy_sync import (
    DeviceNotFoundError,
    InvalidDeviceUUIDError,
    get_policy_sync_payload,
)


sync_bp = Blueprint("sync", __name__)


@sync_bp.get("/sync/policies/<device_uuid>")
def synchronize_policy(device_uuid: str) -> tuple[Response, int]:
    try:
        payload = get_policy_sync_payload(device_uuid)
    except InvalidDeviceUUIDError:
        return jsonify({"error": "invalid device UUID"}), 400
    except DeviceNotFoundError:
        return jsonify({"error": "device not found"}), 404

    return jsonify(payload), 200
