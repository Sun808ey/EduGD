from dataclasses import dataclass

from flask import Request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.device_identity import parse_canonical_uuid4


@dataclass(frozen=True, slots=True)
class PolicyAssignmentRequest:
    policy_revision_uuid: str
    reason: str


class PolicyAssignmentRequestError(ValueError):
    def __init__(self, status_code: int, code: str = "invalid_request") -> None:
        super().__init__("invalid policy assignment request")
        self.status_code = status_code
        self.code = code


def validate_assignment_request(request: Request) -> PolicyAssignmentRequest:
    payload = _json_object(request, {"policy_revision_uuid", "reason"})
    revision_uuid = payload["policy_revision_uuid"]
    reason = _reason(payload["reason"])
    try:
        canonical_revision = parse_canonical_uuid4(revision_uuid)
    except ValueError as error:
        raise PolicyAssignmentRequestError(400) from error
    return PolicyAssignmentRequest(str(canonical_revision), reason)


def validate_clear_request(request: Request) -> str:
    return _reason(_json_object(request, {"reason"})["reason"])


def _json_object(request: Request, expected_keys: set[str]) -> dict[str, object]:
    if request.mimetype != "application/json":
        raise PolicyAssignmentRequestError(415, "unsupported_media_type")
    try:
        payload = request.get_json(silent=False)
    except RequestEntityTooLarge as error:
        raise PolicyAssignmentRequestError(413, "request_too_large") from error
    except BadRequest as error:
        raise PolicyAssignmentRequestError(400) from error
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise PolicyAssignmentRequestError(400)
    return payload


def _reason(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 512
        or not value.isprintable()
    ):
        raise PolicyAssignmentRequestError(400)
    return value


__all__ = [
    "PolicyAssignmentRequest",
    "PolicyAssignmentRequestError",
    "validate_assignment_request",
    "validate_clear_request",
]
