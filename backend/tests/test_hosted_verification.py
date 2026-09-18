import json
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from scripts import verify_hosted_environment as verification


@pytest.mark.parametrize("stage", ["deployment_identity", "application_startup"])
def test_hosted_verification_redacts_dependency_errors(monkeypatch, capsys, stage):
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic-credential-must-not-be-logged")

    monkeypatch.setattr(verification, "validate_deployment_identity", lambda _: None)
    monkeypatch.setattr(
        verification,
        "validate_deployment_identity"
        if stage == "deployment_identity"
        else "create_app",
        fail,
    )
    assert verification.main() == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"hosted_verification": "FAIL", "stage": stage}
    assert not captured.err
    assert "synthetic-credential" not in captured.out


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("root certificate file missing", "ca_file_unavailable"),
        ("password authentication failed", "authentication_failed"),
        ("unexpected error", "connection_failed"),
    ],
)
def test_connection_diagnostics_never_emit_credentials(
    monkeypatch, capsys, message, reason
):
    def fail():
        raise RuntimeError(message + " synthetic-credential-must-not-be-logged")

    monkeypatch.setattr(verification, "validate_deployment_identity", lambda _: None)
    monkeypatch.setattr(
        verification, "create_app", lambda _: SimpleNamespace(app_context=nullcontext)
    )
    monkeypatch.setattr(
        verification, "db", SimpleNamespace(engine=SimpleNamespace(connect=fail))
    )
    monkeypatch.setenv("PRODUCTION_DATABASE_URL", "postgresql://user:synthetic@host/db")
    assert verification.main() == 1
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["stage"] == "database_connection"
    assert result["reason"] == reason
    assert "synthetic" not in captured.out
    assert not captured.err
