from __future__ import annotations

from unittest.mock import Mock

import pytest
from flask import Flask

from app import create_app

ALLOWED_ORIGIN = "http://localhost:5173"
DENIED_ORIGIN = "https://untrusted.example"


def test_admin_cors_allows_configured_origin_on_preflight(app: Flask) -> None:
    response = app.test_client().options(
        "/api/v1/admin/devices",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Headers"] == (
        "Authorization, Content-Type"
    )
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"
    assert response.headers["Vary"] == "Origin"
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_admin_cors_rejects_unconfigured_origin_preflight(app: Flask) -> None:
    response = app.test_client().options(
        "/api/v1/admin/devices",
        headers={
            "Origin": DENIED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 403
    assert "Access-Control-Allow-Origin" not in response.headers


def test_admin_cors_does_not_apply_to_device_api(app: Flask) -> None:
    response = app.test_client().options(
        "/api/v1/devices/register",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "Access-Control-Allow-Origin" not in response.headers


def test_admin_cors_rejects_wildcard_origin() -> None:
    try:
        create_app(
            "testing",
            {
                "ADMIN_FRONTEND_ORIGINS": "*",
            },
        )
    except RuntimeError as error:
        assert "wildcard" in str(error)
    else:
        raise AssertionError("production startup accepted wildcard CORS")


def test_production_requires_admin_frontend_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PRODUCTION_DATABASE_URL",
        "postgresql://ep-production-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require",
    )
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.setattr("app.Redis.from_url", Mock(return_value=Mock()))
    with pytest.raises(RuntimeError, match="Production CORS"):
        create_app(
            "production",
            {
                "SECRET_KEY": "f" * 32,
                "JWT_SECRET_KEY": "j" * 32,
                "ADMIN_AUDIT_PSEUDONYM_KEY": "a" * 32,
                "POLICY_SYNC_AUDIT_KEY": "p" * 32,
                "RATELIMIT_STORAGE_URI": "rediss://redis.example.invalid:6379/0",
            },
        )
