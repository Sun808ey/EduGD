from dataclasses import dataclass

from flask import Request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge


@dataclass(frozen=True, slots=True)
class AdministratorLoginData:
    username: str
    password: str


class AdministratorLoginValidationError(ValueError):
    def __init__(self, status_code: int) -> None:
        super().__init__("invalid administrator login request")
        self.status_code = status_code


def validate_administrator_login_request(
    incoming_request: Request,
) -> AdministratorLoginData:
    if incoming_request.mimetype != "application/json":
        raise AdministratorLoginValidationError(415)

    try:
        payload = incoming_request.get_json(silent=False)
    except RequestEntityTooLarge as error:
        raise AdministratorLoginValidationError(413) from error
    except BadRequest as error:
        raise AdministratorLoginValidationError(400) from error

    if not isinstance(payload, dict) or set(payload) != {"username", "password"}:
        raise AdministratorLoginValidationError(400)

    username = payload["username"]
    password = payload["password"]
    if (
        not isinstance(username, str)
        or not 1 <= len(username) <= 64
        or not isinstance(password, str)
        or not 1 <= len(password) <= 128
    ):
        raise AdministratorLoginValidationError(400)

    return AdministratorLoginData(username=username, password=password)


__all__ = [
    "AdministratorLoginData",
    "AdministratorLoginValidationError",
    "validate_administrator_login_request",
]
