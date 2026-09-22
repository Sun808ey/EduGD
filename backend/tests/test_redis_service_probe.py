"""Safety regression checks for the operator's live Redis probe."""

import sys
from unittest.mock import Mock

import pytest

from scripts import verify_redis_service as probe


@pytest.mark.parametrize(
    "url",
    [
        "redis://user:synthetic-secret@approved.invalid/0",
        "rediss://user:synthetic-secret@other.invalid/0",
        "rediss://user:synthetic-secret@approved.invalid/1",
        "rediss://user:synthetic-secret@approved.invalid/0?ssl_cert_reqs=none",
    ],
)
def test_probe_rejects_wrong_target_or_insecure_url_before_connecting(monkeypatch, url):
    connect = Mock()
    monkeypatch.setattr(probe.Redis, "from_url", connect)
    with pytest.raises(ValueError):
        probe.verify(url, "approved.invalid")
    connect.assert_not_called()


def test_probe_never_prints_provider_exception_secrets(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["probe", "--environment", "staging", "--approve-probe-writes"]
    )
    monkeypatch.setattr(
        probe,
        "verify",
        Mock(
            side_effect=RuntimeError(
                "rediss://user:synthetic-secret@approved.invalid/0"
            )
        ),
    )
    assert probe.main() == 1
    output = capsys.readouterr()
    assert "synthetic-secret" not in output.out + output.err
    assert "details suppressed" in output.out


def test_probe_requires_opt_in_before_any_connection(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["probe", "--environment", "production"])
    verify = Mock()
    monkeypatch.setattr(probe, "verify", verify)
    assert probe.main() == 2
    verify.assert_not_called()
