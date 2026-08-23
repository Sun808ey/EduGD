from __future__ import annotations

import json
from pathlib import Path

from flask import Flask

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"


def test_openapi_documents_frontend_ready_routes(app: Flask) -> None:
    document = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    documented_paths = set(document["paths"])
    expected_paths = {
        "/admin/auth/login",
        "/admin/auth/logout",
        "/admin/auth/me",
        "/admin/devices",
        "/admin/devices/{device_uuid}",
        "/admin/devices/{device_uuid}/policy-assignment",
        "/admin/devices/{device_uuid}/policy-assignment/clear",
        "/admin/policies",
        "/admin/policies/{policy_uuid}",
        "/admin/policies/{policy_uuid}/revisions",
        "/admin/enrollment-tokens",
        "/admin/enrollment-tokens/{token_uuid}/revoke",
        "/admin/audit-events",
        "/devices/register",
        "/devices/{device_uuid}/credentials/rotate",
        "/sync/policies/{device_uuid}",
    }

    assert expected_paths <= documented_paths
    app_paths = {
        rule.rule.removeprefix("/api/v1")
        .replace("<device_uuid>", "{device_uuid}")
        .replace("<policy_uuid>", "{policy_uuid}")
        .replace("<token_uuid>", "{token_uuid}")
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/v1/")
    }
    assert expected_paths <= app_paths
    assert document["components"]["securitySchemes"]["administratorBearer"]


def test_openapi_error_and_pagination_contracts_are_machine_readable() -> None:
    document = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    error = document["components"]["schemas"]["Error"]
    pagination = document["components"]["schemas"]["Pagination"]

    assert error["properties"]["error"]["required"] == ["code", "message"]
    assert pagination["properties"]["per_page"]["maximum"] == 100
