import pytest
from flask import Flask
from flask.testing import FlaskClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import OperationalError

from app.services import readiness


def test_health_endpoint(client: FlaskClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "status": "running",
        "service": "school-policy-api",
    }


def test_readiness_endpoint_reports_ready(client: FlaskClient) -> None:
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "status": "ready",
        "service": "school-policy-api",
    }


def test_readiness_endpoint_fails_closed_without_internal_details(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_check(_: Flask) -> None:
        raise readiness.ReadinessCheckError(
            "database password=private migration revision=internal"
        )

    monkeypatch.setattr("app.routes.health.check_readiness", fail_check)

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "status": "not_ready",
        "service": "school-policy-api",
    }
    assert b"private" not in response.data
    assert b"internal" not in response.data


def test_liveness_remains_available_when_readiness_fails(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_check(_: Flask) -> None:
        raise readiness.ReadinessCheckError("unavailable")

    monkeypatch.setattr("app.routes.health.check_readiness", fail_check)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "running",
        "service": "school-policy-api",
    }


def test_readiness_rejects_missing_essential_configuration(
    app: Flask,
    client: FlaskClient,
) -> None:
    app.config["JWT_SECRET_KEY"] = None

    response = client.get("/api/v1/ready")

    assert response.status_code == 503


def test_readiness_rejects_database_connection_failure(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableEngine:
        def connect(self) -> None:
            raise OperationalError(
                "connection failed",
                {},
                RuntimeError("internal database detail"),
            )

    class UnavailableDatabase:
        engine = UnavailableEngine()

    monkeypatch.setattr(readiness, "db", UnavailableDatabase())

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert b"internal database detail" not in response.data


def test_readiness_rejects_migration_revision_mismatch(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        readiness,
        "_expected_migration_heads",
        lambda: frozenset({"unexpected-revision"}),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503


def test_production_readiness_rejects_unavailable_redis(
    app: Flask,
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.config["APP_ENV"] = "production"
    app.config["RATELIMIT_STORAGE_URI"] = "rediss://redis.example.invalid:6379/0"
    redis_client = type(
        "UnavailableRedis",
        (),
        {"ping": lambda self: (_ for _ in ()).throw(RedisConnectionError())},
    )()
    monkeypatch.setattr(
        readiness.Redis,
        "from_url",
        lambda *_args, **_kwargs: redis_client,
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
