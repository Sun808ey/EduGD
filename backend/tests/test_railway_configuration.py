import json
import runpy
from pathlib import Path

import pytest
from flask import Flask

from app import _admin_frontend_origins

BACKEND = Path(__file__).resolve().parents[1]


def test_railway_runs_migrations_before_workers_and_checks_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = json.loads((BACKEND / "railway.json").read_text())
    assert "db upgrade" not in configuration["build"]["buildCommand"]
    assert configuration["deploy"]["preDeployCommand"] == [
        "flask --app run.py db upgrade"
    ]
    assert (
        configuration["deploy"]["startCommand"]
        == "gunicorn --config gunicorn.conf.py run:app"
    )
    assert configuration["deploy"]["healthcheckPath"] == "/api/v1/ready"
    monkeypatch.setenv("PORT", "8123")
    gunicorn = runpy.run_path(str(BACKEND / "gunicorn.conf.py"))
    assert gunicorn["bind"] == "0.0.0.0:8123"
    assert gunicorn["workers"] == 1
    assert gunicorn["threads"] == 4
    assert gunicorn["access_log_format"] == "%(m)s %(s)s %(L)s"


@pytest.mark.parametrize(
    "origin",
    [
        "http://admin.example.com",
        "https://admin.example.com/",
        "https://user:secret@admin.example.com",
        "https://admin.example.com?x=1",
        "https://admin.example.com#x",
        "https://admin.example.com:bad",
        "https://admin.example.com:99999",
        "https://",
        "https://a b",
        "https://a\\b",
    ],
)
def test_production_cors_rejects_non_origin_configuration(origin: str) -> None:
    app = Flask(__name__)
    app.config.update(APP_ENV="production", ADMIN_FRONTEND_ORIGINS=origin)
    with pytest.raises(RuntimeError, match="HTTPS origins"):
        _admin_frontend_origins(app)


def test_exact_production_origins_and_development_localhost_remain_supported() -> None:
    app = Flask(__name__)
    app.config.update(
        APP_ENV="production",
        ADMIN_FRONTEND_ORIGINS="https://admin.example.com,https://admin.example.com:8443",
    )
    assert len(_admin_frontend_origins(app)) == 2
    app.config.update(
        APP_ENV="development", ADMIN_FRONTEND_ORIGINS="http://localhost:5173"
    )
    assert _admin_frontend_origins(app) == frozenset({"http://localhost:5173"})
