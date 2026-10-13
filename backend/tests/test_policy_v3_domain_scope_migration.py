import importlib.util
from pathlib import Path


def _migration_module():
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "k6l7m8n9o0_backfill_legacy_dpc_v3_domain_scope.py"
    )
    spec = importlib.util.spec_from_file_location("policy_v3_domain_scope", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_materialises_explicit_domain_scope() -> None:
    migration = _migration_module()
    payload = {
        "schema_version": 3,
        "web_filter": {
            "default_action": "allow",
            "rules": [
                {
                    "rule_id": "blocked_domain",
                    "domain": "example.com",
                    "action": "block",
                    "reason": "School policy",
                }
            ],
        },
    }

    result = migration._backfilled_payload(payload)

    assert result is not None
    assert result["web_filter"]["rules"][0]["include_subdomains"] is True
    assert "include_subdomains" not in payload["web_filter"]["rules"][0]


def test_backfill_does_not_duplicate_complete_domain_scope() -> None:
    migration = _migration_module()
    payload = {
        "schema_version": 3,
        "web_filter": {
            "default_action": "allow",
            "rules": [
                {
                    "rule_id": "blocked_domain",
                    "domain": "example.com",
                    "include_subdomains": True,
                    "action": "block",
                    "reason": "School policy",
                }
            ],
        },
    }

    assert migration._backfilled_payload(payload) is None
