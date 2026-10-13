import importlib.util
from pathlib import Path


def _migration_module():
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "j5k6l7m8n9_backfill_legacy_dpc_v3_controls.py"
    )
    spec = importlib.util.spec_from_file_location("policy_v3_backfill", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_adds_only_missing_required_control_sections() -> None:
    migration = _migration_module()
    payload = {
        "schema_version": 3,
        "timezone": "Africa/Kampala",
        "web_filter": {"default_action": "allow", "rules": []},
    }

    result = migration._backfilled_payload(payload)

    assert result is not None
    assert result["network_controls"] == migration.DEFAULT_NETWORK_CONTROLS
    assert result["telephony_controls"] == migration.DEFAULT_TELEPHONY_CONTROLS
    assert payload == {
        "schema_version": 3,
        "timezone": "Africa/Kampala",
        "web_filter": {"default_action": "allow", "rules": []},
    }


def test_backfill_does_not_duplicate_complete_payloads() -> None:
    migration = _migration_module()
    payload = {
        "schema_version": 3,
        "network_controls": dict(migration.DEFAULT_NETWORK_CONTROLS),
        "telephony_controls": dict(migration.DEFAULT_TELEPHONY_CONTROLS),
    }

    assert migration._backfilled_payload(payload) is None
