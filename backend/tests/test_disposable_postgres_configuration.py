from pathlib import Path

import yaml

from test_support.postgres_safety import validate_postgres_test_environment


def test_disposable_stack_cannot_publish_database_or_use_hosted_secrets() -> None:
    configuration = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "compose.postgres-test.yml").read_text()
    )
    assert configuration["networks"]["isolated"]["internal"] is True
    for service in configuration["services"].values():
        assert "ports" not in service
        assert "env_file" not in service
        assert "network_mode" not in service
    values = configuration["services"]["tests"]["environment"]
    password_reference = "${EDUG_DISPOSABLE_POSTGRES_TOKEN:?required}"
    assert values["POSTGRES_TEST_DATABASE_URL"].count(password_reference) == 1
    assert values["MIGRATION_DATABASE_URL"].count(password_reference) == 1
    assert configuration["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"] == password_reference
    resolved_values = {
        name: value.replace(password_reference, "generated-for-this-test")
        for name, value in values.items()
    }
    approved = validate_postgres_test_environment(
        resolved_values, require_destructive=True
    )
    assert (
        f"db.{approved.project_ref}.supabase.co"
        in configuration["services"]["postgres"]["networks"]["isolated"]["aliases"]
    )
