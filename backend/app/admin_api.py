from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from flask import Response, jsonify, request

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


@dataclass(frozen=True, slots=True)
class Pagination:
    page: int
    per_page: int
    offset: int


class AdminRequestError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def parse_pagination() -> Pagination:
    page = _bounded_integer("page", default=1, minimum=1, maximum=10_000)
    per_page = _bounded_integer(
        "per_page",
        default=DEFAULT_PAGE_SIZE,
        minimum=1,
        maximum=MAX_PAGE_SIZE,
    )
    return Pagination(page=page, per_page=per_page, offset=(page - 1) * per_page)


def parse_optional_filter(name: str, allowed_values: frozenset[str]) -> str | None:
    raw_value = request.args.get(name)
    if raw_value is None:
        return None
    if raw_value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise AdminRequestError(
            "invalid_filter",
            f"{name} must be one of: {allowed}",
        )
    return raw_value


def admin_json(payload: dict[str, object], status_code: int = 200) -> Response:
    response = jsonify(payload)
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


def admin_error(code: str, message: str, status_code: int) -> Response:
    return admin_json({"error": {"code": code, "message": message}}, status_code)


def pagination_payload(
    pagination: Pagination,
    *,
    total: int,
) -> dict[str, int | bool]:
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": total,
        "has_next": pagination.offset + pagination.per_page < total,
    }


def isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _bounded_integer(
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    if not raw_value.isdecimal():
        raise AdminRequestError(
            "invalid_pagination",
            f"{name} must be a base-10 integer",
        )
    value = int(raw_value, 10)
    if not minimum <= value <= maximum:
        raise AdminRequestError(
            "invalid_pagination",
            f"{name} must be between {minimum} and {maximum}",
        )
    return value


__all__ = [
    "AdminRequestError",
    "Pagination",
    "admin_error",
    "admin_json",
    "isoformat_utc",
    "pagination_payload",
    "parse_optional_filter",
    "parse_pagination",
]
