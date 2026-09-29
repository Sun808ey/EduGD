"""Response helpers for authenticated device-facing endpoints."""

from __future__ import annotations

from flask import Response, jsonify


def device_json(payload: dict[str, object], status_code: int = 200) -> Response:
    response = jsonify(payload)
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


def device_error(code: str, status_code: int) -> Response:
    return device_json({"error": code}, status_code)
