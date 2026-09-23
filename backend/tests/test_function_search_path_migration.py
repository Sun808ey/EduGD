"""Unit coverage for the PostgreSQL function-hardening migration."""

from __future__ import annotations

import importlib
from types import SimpleNamespace


def test_function_hardening_migration_sets_a_fixed_search_path(monkeypatch) -> None:
    migration = importlib.import_module(
        "migrations.versions.ab4e6f2c9d71_harden_postgres_function_search_paths"
    )
    statements: list[str] = []
    monkeypatch.setattr(
        migration.op,
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    rendered = "\n".join(statements)
    assert "SET search_path = ''" in rendered
    assert "edug_reject_device_control_event_mutation()" in rendered
    assert "public.edug_valid_blocked_apps(value->'blocked_apps')" in rendered
    assert "REVOKE ALL ON FUNCTION public.edug_valid_blocked_apps(value json) FROM PUBLIC" in rendered
    assert "GRANT EXECUTE ON FUNCTION public.edug_valid_blocked_apps(value json) TO edug_runtime" in rendered


def test_function_hardening_migration_is_a_noop_on_sqlite(monkeypatch) -> None:
    migration = importlib.import_module(
        "migrations.versions.ab4e6f2c9d71_harden_postgres_function_search_paths"
    )
    monkeypatch.setattr(
        migration.op,
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")),
    )
    monkeypatch.setattr(
        migration.op,
        "execute",
        lambda statement: (_ for _ in ()).throw(AssertionError(statement)),
    )

    migration.upgrade()
