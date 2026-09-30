import os
import runpy
from pathlib import Path

import pytest
from flask import Flask

import app as application_package
import app.deployment_identity as deployment_identity
from app.device_api import device_error, device_json
from app.dpc_capability_catalogue import validate_capabilities

BACKEND = Path(__file__).resolve().parents[1]


def test_device_responses_disable_caching() -> None:
    application = Flask(__name__)

    with application.app_context():
        response = device_json({"status": "ok"})
        error = device_error("invalid_device", 403)

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert error.status_code == 403
    assert error.get_json() == {"error": "invalid_device"}
    assert error.headers["Cache-Control"] == "no-store"


def test_gunicorn_configuration_uses_the_platform_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PORT", "8123")

    configuration = runpy.run_path(str(BACKEND / "app" / "gunicorn_config.py"))

    assert configuration["bind"] == "0.0.0.0:8123"
    assert configuration["workers"] == 1
    assert configuration["threads"] == 4
    assert configuration["timeout"] == 30
    assert configuration["graceful_timeout"] == 30
    assert configuration["accesslog"] == "-"
    assert configuration["errorlog"] == "-"


def test_wsgi_validates_identity_before_creating_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    application = object()

    def validate(environment: object) -> None:
        calls.append(("validate", environment))

    def create(configuration: str) -> object:
        calls.append(("create", configuration))
        return application

    monkeypatch.setattr(deployment_identity, "validate_deployment_identity", validate)
    monkeypatch.setattr(application_package, "create_app", create)

    namespace = runpy.run_path(str(BACKEND / "app" / "wsgi.py"))

    assert calls == [("validate", os.environ), ("create", "production")]
    assert namespace["app"] is application


def test_capability_catalogue_rejects_unknown_capability() -> None:
    with pytest.raises(ValueError, match="unknown or unsupported"):
        validate_capabilities(["unknown_capability"], api_level=35)
