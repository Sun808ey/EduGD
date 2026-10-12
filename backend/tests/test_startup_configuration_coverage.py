from __future__ import annotations

import pytest

import app as application_module


def test_startup_configuration_rejects_unsafe_sunbird_and_enrollment_values(
    app,
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "token"
    app.config["SUNBIRD_API_BASE_URL"] = "http://sunbird.example"
    with pytest.raises(RuntimeError):
        application_module._validate_startup_configuration(app)
    app.config["SUNBIRD_API_BASE_URL"] = "https://user:pass@sunbird.example/path?x=1"
    with pytest.raises(RuntimeError):
        application_module._validate_startup_configuration(app)
    app.config["SUNBIRD_API_TOKEN"] = object()
    with pytest.raises(RuntimeError):
        application_module._validate_startup_configuration(app)

    app.config["SUNBIRD_API_TOKEN"] = None
    app.config["DEVICE_ENROLLMENT_MODE"] = "unsupported"
    with pytest.raises(RuntimeError):
        application_module._validate_startup_configuration(app)
    app.config["DEVICE_ENROLLMENT_MODE"] = "legacy"
    app.config["ENROLLMENT_ADMIN_ENABLED"] = True
    app.config["PAIRING_TOKEN_PEPPER"] = "short"
    with pytest.raises(RuntimeError):
        application_module._validate_startup_configuration(app)


def test_admin_frontend_origins_and_vary_helpers(app) -> None:
    app.config["ADMIN_FRONTEND_ORIGINS"] = None
    assert application_module._admin_frontend_origins(app) == frozenset()
    app.config["ADMIN_FRONTEND_ORIGINS"] = "*"
    with pytest.raises(RuntimeError):
        application_module._admin_frontend_origins(app)
    app.config["ADMIN_FRONTEND_ORIGINS"] = 1
    with pytest.raises(RuntimeError):
        application_module._admin_frontend_origins(app)
    assert application_module._append_vary(None, "Origin") == "Origin"
    assert application_module._append_vary("Accept", "Origin") == "Accept, Origin"
    assert (
        application_module._append_vary("Accept, Origin", "Origin") == "Accept, Origin"
    )
